"""Coordinates revision state, shared history and independent sessions."""
from __future__ import annotations

import asyncio
import json
from typing import Any

import websockets

from server.client_session import ClientSession, handle_client
from server.delivery_hub import DeliveryHub
from server.history import FinalHistory
from server.source_session import handle_source
from server.state import CaptionState, CaptionSegment


class LiveRecallApplication:
    def __init__(self, semantic_backpressure=True):
        # Remembers the latest accepted provisional and which segments are finalized
        self.caption_state = CaptionState(session="L1")
        # Stores recent final captions, shared by all clients. Default retention is 70 seconds
        self.final_history = FinalHistory()
        # Keeps track of registered client sessions and distributes accepted captions to them
        self.delivery_hub = DeliveryHub()
        # Controls whether slow clients’ outdated provisional updates can be collapsed
        self.semantic_backpressure = semantic_backpressure
        # Prevents server operations such as updating caption state and registering clients from interleaving, which could result in race condition
        self._lock = asyncio.Lock()

    @property
    def connected_client_count(self):
        return self.delivery_hub.client_count

    # Identifies and handles either a caption source or a client connection
    async def handle_connection(self, websocket: Any) -> None:
        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=5)
            hello = json.loads(raw)
        except (asyncio.TimeoutError, json.JSONDecodeError):
            await websocket.close(code=1008, reason="Expected a valid hello message")
            return
        if not isinstance(hello, dict):
            await websocket.close(code=1008, reason="Expected a hello object")
            return
        # If hello message is from a caption source
        if hello.get("type") == "SOURCE_HELLO":
            await handle_source(websocket, hello, self.process_source_update)
        # If hello message is from a client
        elif hello.get("type") == "CLIENT_HELLO":
            await handle_client(websocket, hello, self)
        else:
            await websocket.close(code=1008, reason="Expected SOURCE_HELLO or CLIENT_HELLO")

    # Processes a caption coming from the source
    async def process_source_update(self, message: dict[str, Any]) -> CaptionSegment | None:
        async with self._lock:
            # Uses details from CaptionState to determine if caption received is old or duplicate or alr finalized segement, if accepted caption is a final, it is added to the shared final history
            accepted = self.caption_state.accept_update(message, self.final_history.add)
            # If caption is accepted, publish to all independent senders
            if accepted is not None:
                self.delivery_hub.publish(accepted.to_dict())
        if accepted is not None:
            await asyncio.sleep(0)
        return accepted

    # Registers a new client session and sends it the recent finalized captions from shared history
    async def attach_client(self, client: ClientSession, last_segment: int,
                            last_revision: int, history_seconds: int) -> None:
        async with self._lock:
            history_items = self.final_history.get_recent(
                seconds=history_seconds, last_segment=last_segment,
                last_revision=last_revision)
            client.set_initial_history(history_items)
            self.delivery_hub.register_client(client)

    async def detach_client(self, client: ClientSession) -> None:
        async with self._lock:
            self.delivery_hub.unregister_client(client)
        await client.close()

# Create an instance of the server application
async def run_server(port: int, semantic_backpressure: bool = True) -> None:
    application = LiveRecallApplication(semantic_backpressure)
    async with websockets.serve(
        application.handle_connection, "0.0.0.0", port,
        max_size=2**20, ping_interval=20, ping_timeout=20,
        close_timeout=2, write_limit=32768,
    ):
        print(f"LiveRecall listening on ws://0.0.0.0:{port}", flush=True)
        await asyncio.Future()
