import asyncio
import json
import websockets

from typing import Any, TYPE_CHECKING
from enum import Enum, auto
from server.config import (
    CLIENT_QUEUE_HIGH_WATERMARK,
    CLIENT_QUEUE_LOW_WATERMARK,
    CLIENT_QUEUE_MAXSIZE,
    CLIENT_SEND_TIMEOUT
)
from server.history import FinalHistory
from server.protocol import (
    CaptionUpdateMessage,
    HistoryMessage,
    OutgoingMessage
)
from server.semantic_queue import AddResult, SemanticQueue

if TYPE_CHECKING:
    from server.application import LiveRecallApplication

class CongestionMode(Enum):
    NORMAL = auto()
    CONGESTED = auto()
class ClientSession:

    def __init__(
        self,
        *,
        client_id: int,
        websocket: Any, # unique to each client session
        history: FinalHistory, # same reference FinalHistory object for every client
        initial_history_items: list[CaptionUpdateMessage], # the initial history item from CLIENT HELLO

        queue_max_size: int = CLIENT_QUEUE_MAXSIZE,
        high_watermark: int = CLIENT_QUEUE_HIGH_WATERMARK,
        low_watermark: int = CLIENT_QUEUE_LOW_WATERMARK,
        send_timeout: float = CLIENT_SEND_TIMEOUT,
        semantic_backpressure: bool = True,
    ) -> None:
        self.client_id = client_id
        self.websocket = websocket
        self.history = history

        # initial "HISTORY" message, becomes "None" after it is sent
        self.initial_history: HistoryMessage | None = (
            history.get_history_message_format(initial_history_items)
        )

        # the next final sequence number that the server need to send to this client (for live updates)
        # it is history.next_sequence because that is the segment that hasn't been finalised yet
        # next_sequence - 1 are already Final, so they will be sent to client under HISTORY message
        self.next_final = history.next_sequence

        # used to store provisional segments only (for live updates)
        self.provisional_queue = SemanticQueue(
            max_size=queue_max_size,
            high_watermark=high_watermark,
            low_watermark=low_watermark,
            semantic_backpressure=semantic_backpressure,
        )

        self.send_timeout = send_timeout # used in websocket.wait_for()
        self.ready = asyncio.Event() # wake up bell for the sender task

        self.sender_task: asyncio.Task[None] | None = None
        self._is_closed = False

    @property
    def is_closed(self):
        return self._is_closed


    # used in delivery_hub.publish() to send live updates to all clients
    def offer(self, message: CaptionUpdateMessage) -> AddResult:
        """Make a live update available to this client."""

        if self.is_closed:
            return AddResult.CLOSED

        # case 1: message is Final
        if message["final"]:
            # The final is already in shared FinalHistory.
            # Wake the sender so it checks its next_final cursor.
            self.ready.set()
            return AddResult.ENQUEUED

        # case 2: message is NOT Final
        result = self.provisional_queue.add_message(message)

        if result in { AddResult.ENQUEUED, AddResult.COALESCED }:
            self.ready.set()

        return result

    async def send_message(self, message: OutgoingMessage) -> None:
        """Encode and send message using websocket"""

        encoded = json.dumps(message)

        await asyncio.wait_for(
            self.websocket.send(encoded),
            timeout=self.send_timeout,
        )

    async def sender_loop(self) -> None:
        """Send initial history, provisionals and cursor based finals."""

        try:
            if self.initial_history is not None:
                await self.send_message(self.initial_history)
                self.initial_history = None # after sending, set to None

            while True:
                # throws LookupError if client fell behind retained final history
                final_entry = self.history.get_entry(self.next_final)

                provisional = self.provisional_queue.peek_message()

                # Preserve source order. A provisional for the same or an
                # earlier segment must be sent before that segment's final.
                # provisional exist && provisional segmentID <= final.segmentID
                if ( 
                    provisional is not None
                    and (
                        final_entry is None
                        or provisional["segment"] <= final_entry.caption.segment_id
                    )
                ):
                    provisional = self.provisional_queue.pop_message()

                    if provisional is not None:
                        await self.send_message(provisional)

                    continue

                # provisional doesn't exist OR provisional segmentID > final.segmentID
                # --> send final segment before the provisional segment
                if final_entry is not None:
                    await self.send_message(final_entry.caption.to_dict())

                    # Advance only after successful sending
                    self.next_final += 1
                    continue

                # No work -- final_entry is None && provisional is None -- fully catched up
                # Clear the event flag and then recheck to avoid missing a wake-up.
                self.ready.clear()

                # recheck to avoid missing a wake up
                if self.provisional_queue.peek_message() is not None:
                    continue

                # recheck to avoid missing a wake up
                if self.history.get_entry(self.next_final) is not None:
                    continue

                await self.ready.wait()

        except LookupError:
            # This client's next final has expired from bounded history,
            # so disconnect the client
            await self.websocket.close(
                code=1013,
                reason="Client fell behind retained history",
            )
            raise

        except websockets.ConnectionClosed:
            pass

        except asyncio.CancelledError:
            raise

    async def run(self):
        """Runs until sending ends"""

        if self.is_closed:
            return

        self.sender_task = asyncio.create_task( # a asyncio Task that keeps looping and sending message to client
            self.sender_loop(),
            name=f"client-{self.client_id}-sender-task" # easier for debugging :)
        )

        connection_close_task = asyncio.create_task(
            self.websocket.wait_closed(),
            name=f"client-{self.client_id}-wait-closed-task"
        )

        tasks = {
            self.sender_task,
            connection_close_task
        }

        try:
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED
            )

            # raise the exception, for example if json.dumps fails
            for task in done:
                if not task.cancelled():
                    exception = task.exception()

                    if exception is not None:
                        raise exception
                    
            for task in pending:
                task.cancel()

            await asyncio.gather(*pending, return_exceptions=True)

        finally:
            # close client session when one of the tasks in completed
            self._is_closed = True

            for task in tasks:
                if not task.done():
                    task.cancel()

            await asyncio.gather(*tasks, return_exceptions=True)

            await self.websocket.close()


    async def close(self, reason: str = "Client session closed") -> None:
        """Close client connection"""
        if self.is_closed:
            return

        self._is_closed = True

        await self.websocket.close(code=1013,reason=reason)


def parse_client_hello(hello:dict[str, Any]) -> tuple[int, int, int]:
    """Parse the CLIENT HELLO message recovery value

    Note: client with no previous state will have last_segment = 0, last_revision = 0
    Since the document didn't specify what the history_seconds should be,
    we specify the client to send "history_seconds": 60 
    """

    last_segment = hello.get("last_segment")
    last_revision = hello.get("last_revision")
    history_seconds = hello.get("history_seconds")

    if type(last_segment) is not int or last_segment < 0:
        last_segment = 0

    if type(last_revision) is not int or last_revision < 0:
        last_revision = 0

    if type(history_seconds) is not int or history_seconds < 0:
        history_seconds = 30

    if history_seconds > 60:
        history_seconds = 60

    return last_segment, last_revision, history_seconds



async def handle_client(
    websocket, 
    hello: dict[str, Any], 
    application: LiveRecallApplication
) -> None:

    client_id = hello.get("client_id")

    if hello.get("session") != "L1":
        await websocket.close(code=1008, reason="Invalid session")
        return

    last_segment, last_revision, history_seconds = parse_client_hello(hello)

    client: ClientSession | None = None

    try:
        client = await application.attach_client( # insert history into client queue & register client into delivery hub
            websocket=websocket,
            client_id=client_id,
            last_segment=last_segment,
            last_revision=last_revision,
            history_seconds=history_seconds,
        )

        print(
            f"client connected: id={client_id}; "
            f"clients={application.connected_client_count}",
            flush=True,
        )

        await client.run() # run the client sender task which sends message in a while loop

    finally: # close the connection
        if client is not None:
            await application.detach_client(client)
        else:
            await websocket.close()

        print(f"client disconnected: id={client_id}; clients={application.connected_client_count}", flush=True)
