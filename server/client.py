"""Independent FIFO delivery for one LiveRecall client."""

from __future__ import annotations

import asyncio
from collections import deque
from contextlib import suppress
from typing import Any

class Client:
    """
    Owns the application queue and sender for one WebSocket.
    Makes enqueuing a broadcast cheap and prevents one client blocking others.
    """

    def __init__(self, ws: Any, client_id: Any):
        self.ws = ws
        self.client_id = client_id
        self._pending: deque[str] = deque()
        self._available = asyncio.Event()
        self._sender_task: asyncio.Task[None] | None = None
        self._stopped = False

    def start(self) -> None:
        if self._sender_task is None:
            self._sender_task = asyncio.create_task(self.send_loop(), name=f"client-sender-{self.client_id}")

    def append(self, payload: str) -> bool:
        if self._stopped:
            return False
        self._pending.append(payload)
        self._available.set()
        return True

    async def send_loop(self) -> None:
        try:
            while not self._stopped:
                if not self._pending:
                    self._available.clear()
                    await self._available.wait()
                    continue

                payload = self._pending.popleft()
                await self.ws.send(payload)
        except asyncio.CancelledError:
            raise
        except Exception:
            # A failed send makes the connection unusable. Closing wakes the
            # receive side of the client handler, which performs cleanup.
            self._stopped = True
            with suppress(Exception):
                await self.ws.close()

    async def stop(self) -> None:
        self._stopped = True
        self._available.set()
        if self._sender_task is not None:
            self._sender_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._sender_task

