import asyncio
from email.mime import application
from pydoc import cli
import websockets
import json

from server.history import FinalHistory
from server.state import CaptionSegment, CaptionState
from server.delivery_hub import ClientSession, DeliveryHub
from server.source_session import handle_source
from server.client_session import handle_client
from typing import Any


class LiveRecallApplication:
    """Coordinates shared server state, history and connection delivery"""

    def __init__(self):
        self.caption_state = CaptionState(session="L1")
        self.final_history = FinalHistory()
        self.delivery_hub = DeliveryHub()

        self._lock = asyncio.Lock()

    @property
    def connected_client_count(self):
        return self.delivery_hub.client_count

    async def handle_connection(self, websocket: Any) -> None:
        """Read the HELLO message and route the connection"""

        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=5) # receive initial CLIENT HELLO message (timeout 5 seconds)
            hello = json.loads(raw)
        except (asyncio.TimeoutError, json.JSONDecodeError):
            await websocket.close(code=1008, reason="Expected a valid hello message")
            return

        msg_type = hello.get("type")
        if msg_type == "SOURCE_HELLO": # caption source
            await handle_source(websocket, hello, self.process_source_update) # pass a callback function :)
        elif msg_type == "CLIENT_HELLO": # client initiate connection
            await handle_client(websocket, hello, self)
        else:
            await websocket.close(code=1008, reason="Expected SOURCE_HELLO or CLIENT_HELLO")

    async def process_source_update(self, message: dict[str, Any]) -> CaptionSegment | None:
        """Parse and create ClientSegment object, update FinalHistory if is final segment,
        then publish it to all clients
        
        Returns the parsed, accepted segment
        """

        clients_to_close: list[ClientSession] = []

        async with self._lock:
            # parse the message and get a CaptionSegment object
            accepted_segment = self.caption_state.accept_update(message)

            if accepted_segment is None:
                return None

            # Final must enter shared history before clients are notified.
            if accepted_segment.final:
                self.final_history.add(accepted_segment)

            clients_to_close = self.delivery_hub.publish(
                accepted_segment.to_dict()
            )

        # Disconnect clients where delivery_hub.publish() fails to send them message due to overflow / session closed
        await asyncio.gather(
            *(
                client.close(
                    reason="Unable to maintain bounded delivery state"
                )
                for client in clients_to_close
            ),
            return_exceptions=True,
        )

        return accepted_segment

    async def attach_client(
        self,
        *,
        websocket: Any,
        client_id: int,
        last_segment: int,
        last_revision: int,
        history_seconds: int,
    ) -> ClientSession:
        """
        Create a new ClientSession and insert tthe initial history items and register
        the client in delivery hub
        """
        
        async with self._lock:
            # get the history segment needed based on client hello value
            history_items = self.final_history.get_recent(
                seconds=history_seconds,
                last_segment=last_segment,
                last_revision=last_revision
            )

            client = ClientSession(
                client_id=client_id,
                websocket=websocket,
                history=self.final_history,
                initial_history_items=history_items,
            )

            self.delivery_hub.register_client(client)

        return client

    async def detach_client(self, client: ClientSession):
        """Remove client from delivery hub and close client session
        
        Will invoke client.close() here
        """

        async with self._lock:
            self.delivery_hub.unregister_client(client)

        await client.close()


async def run_server(port: int) -> None:
    application = LiveRecallApplication()

    async with websockets.serve(
        application.handle_connection,
        "0.0.0.0",
        port,
        max_size=2**20,
        ping_interval=20,
        ping_timeout=20,
    ):
        print(f"LiveRecall baseline listening on ws://0.0.0.0:{port}", flush=True)
        await asyncio.Future() # run forever
    