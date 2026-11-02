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
        self.caption_state = CaptionState(session="L1")
        self.final_history = FinalHistory()
        self.delivery_hub = DeliveryHub()
        self.semantic_backpressure = semantic_backpressure
        self._lock = asyncio.Lock()

    @property
    def connected_client_count(self):
        return self.delivery_hub.client_count

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
        if hello.get("type") == "SOURCE_HELLO":
            await handle_source(websocket, hello, self.process_source_update, self.caption_state)
        elif hello.get("type") == "CLIENT_HELLO":
            await handle_client(websocket, hello, self)
        else:
            await websocket.close(code=1008, reason="Expected SOURCE_HELLO or CLIENT_HELLO")

    async def process_source_update(self, message: dict[str, Any]) -> CaptionSegment | None:
        async with self._lock:
            # Persist before committing final state; a capacity failure remains retryable.
            accepted = self.caption_state.accept_update(message, self.final_history.add)
            if accepted is not None:
                self.delivery_hub.publish(accepted.to_dict())
        if accepted is not None:
            # Buffered source reads and uncontended locks may not yield themselves.
            await asyncio.sleep(0)
        return accepted

    async def attach_client(self, client: ClientSession, last_segment: int,
                            last_revision: int, history_seconds: int) -> None:
        async with self._lock:
            history_items = self.final_history.get_recent(
                seconds=history_seconds, last_segment=last_segment,
                last_revision=last_revision)
            # Snapshot, cursor capture and registration are one transaction.
            # There are no network waits in this section.
            client.set_initial_history(history_items)
            self.delivery_hub.register_client(client)

    async def detach_client(self, client: ClientSession) -> None:
        async with self._lock:
            self.delivery_hub.unregister_client(client)
        await client.close()


async def run_server(port: int, semantic_backpressure: bool = True) -> None:
    application = LiveRecallApplication(semantic_backpressure)
    async with websockets.serve(
        application.handle_connection, "0.0.0.0", port,
        max_size=2**20, ping_interval=20, ping_timeout=20,
        close_timeout=2, write_limit=32768,
    ):
        print(f"LiveRecall listening on ws://0.0.0.0:{port}", flush=True)
        await asyncio.Future()
