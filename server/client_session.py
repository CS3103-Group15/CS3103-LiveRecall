import asyncio
import json
from typing import Any, TYPE_CHECKING

import websockets

from server.protocol import CaptionUpdateMessage, HistoryMessage

if TYPE_CHECKING:
    from server.application import LiveRecallApplication

OutgoingMessage = CaptionUpdateMessage | HistoryMessage

class ClientSession:

    def __init__(
        self, 
        client_id: int,
        websocket: Any,
        queue_max_size: int = 128
    ):
        self.client_id = client_id
        self.websocket = websocket
        self.outgoing_queue: asyncio.Queue[OutgoingMessage] = ( # each client session has its own queue
            asyncio.Queue(maxsize=queue_max_size)
        )

        self.sender_task: asyncio.Task[None] | None = None
        self._is_closed = False

    @property
    def is_closed(self):
        return self._is_closed

    def enqueue(self, message: OutgoingMessage) -> bool:
        """Attempt to enqueue a messsage without waiting
        
        Return false if the queue is full or session is closed"""

        if self.is_closed:
            return False

        try:
            self.outgoing_queue.put_nowait(message) # insert the message into queue without waiting
        except asyncio.QueueFull: # queue is full, return False
            return False

        return True

    async def sender_loop(self) -> None:
        """Send message from this client queue in FIFO
        
        Runs in a loop a fetch message from queue.
        - If queue is not empty, then extract the message and send it.
        - If queue is empty, suspend the execution at the retrival point and then
          give control back to asyncio event loop so other concurrent tasks can
          run without CPU overhead
        """

        try:
            while True:
                message = await self.outgoing_queue.get()

                try:
                    encoded_msg = json.dumps(message)
                    await self.websocket.send(encoded_msg)

                finally:
                    self.outgoing_queue.task_done() # tells the queue that the fetch message has been processed

        except websockets.ConnectionClosed:
            # client connection is closed, cleanup is handled by run()
            pass

        except asyncio.CancelledError:
            # expected when clientsession is shutting down
            raise

    async def run(self):
        """Runs until sending ends"""

        if self.is_closed:
            return

        self.sender_task = asyncio.create_task( # a task that keeps looping and sending message to client
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

    async def close(self):
        """Close client session without doing application unregistering in delivery hub"""

        # make sure websocket is close only once
        if self.is_closed:
            return
        self._is_closed = True

        await self.websocket.close(code=1013, reason="Client session closed")



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
    """Create and manage ClientSession"""

    client_id = hello.get("client_id")

    if hello.get("session") != "L1":
        await websocket.close(code=1008, reason="Invalid session")
        return

    last_segment, last_revision, history_seconds = parse_client_hello(hello)

    client = ClientSession(
        client_id=client_id,
        websocket=websocket,
    )

    registered = False

    try:
        await application.attach_client( # insert history into client queue & register client into delivery hub
            client,
            last_segment,
            last_revision,
            history_seconds
        )

        registered = True
        print(
            f"client connected: id={client_id}; "
            f"clients={application.connected_client_count}",
            flush=True,
        )

        await client.run() # run the client sender task which sends message in a while loop

    finally: # close the connection
        if registered:
            await application.detach_client(client)
        else:
            await client.close()

        print(f"client disconnected: id={client_id}; clients={application.connected_client_count}", flush=True)
