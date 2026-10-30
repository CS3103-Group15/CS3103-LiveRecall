import asyncio
from email.mime import application
from pydoc import cli
import websockets
import json

from server.history import FinalHistory
from server.state import CaptionState
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
            await handle_source(websocket, hello, self.process_source_update)
        elif msg_type == "CLIENT_HELLO": # client initiate connection
            await handle_client(websocket, hello, self)
        else:
            await websocket.close(code=1008, reason="Expected SOURCE_HELLO or CLIENT_HELLO")

    async def process_source_update(self, message: dict[str, Any]) -> None:
        """Accept, store and publish one source update"""

        async with self._lock:
            accepted = self.caption_state.accept_update(message)

            if accepted is None:
                return None

            if accepted.final:
                self.final_history.add(accepted)

            self.delivery_hub.publish(accepted.to_dict())

    async def attach_client(
        self,
        client: ClientSession,
        last_segment: int,
        last_revision: int,
        history_seconds: int,
    ) -> None:
        """Queue history segments and register a client for live updates"""
        
        # get the history segment needed based on client hello value
        async with self._lock:
            history_items = self.final_history.get_recent(
                seconds=history_seconds,
                last_segment=last_segment,
                last_revision=last_revision
            )

            history_message = self.final_history.get_history_message_format(history_items)

            # history must be the First queued message !!!
            if not client.enqueue(history_message):
                raise RuntimeError("Unable to queue initial client history")

        # register client into delivery hub for live updates :)
        self.delivery_hub.register_client(client)

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
    