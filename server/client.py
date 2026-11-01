"""Bounded, revision-aware delivery for one LiveRecall client."""

from __future__ import annotations

import asyncio
from collections import deque
from contextlib import suppress
from typing import Any


class PendingMessage:
    def __init__(self, payload: str, segment: int | None = None, revision: int | None = None, final: bool = False):
        self.payload = payload
        self.segment = segment
        self.revision = revision
        self.final = final


class Client:
    """
    Owns the bounded application queue and sender for one WebSocket.
    Makes enqueuing a broadcast cheap and prevents one client blocking others.
    """

    QUEUE_CAPACITY = 64
    PRESSURE_THRESHOLD = 32

    def __init__(self, ws: Any, client_id: Any):
        self.ws = ws
        self.client_id = client_id
        self._pending: deque[PendingMessage] = deque()
        self._available = asyncio.Event()
        self._sender_task: asyncio.Task[None] | None = None
        self._stopped = False
        self.overflowed = False
        self.sent_count = 0
        self.coalesced_count = 0

    def start(self) -> None:
        if self._sender_task is None:
            self._sender_task = asyncio.create_task(self.send_loop(), name=f"client-sender-{self.client_id}")

    def append(self, payload: str, *, segment: int | None = None, revision: int | None = None, final: bool = False) -> bool:
        if self._stopped:
            return False

        item = PendingMessage(payload=payload, segment=segment, revision=revision, final=final)

        # Below the soft threshold, preserve every revision for normal update
        # coverage. Once this client's backlog reaches the threshold, remove
        # only provisional messages made obsolete by newer semantic state.
        if segment is not None and len(self._pending) + 1 >= self.PRESSURE_THRESHOLD:
            self._coalesce(item)

        if len(self._pending) >= self.QUEUE_CAPACITY:
            self._overflow()
            return False

        self._pending.append(item)
        self._available.set()
        return True

    def _coalesce(self, incoming: PendingMessage) -> None:
        """Keep durable messages and only the newest useful provisional state."""
        queued_finals = {item.segment for item in self._pending if item.final}

        # Find the last/newest queued provisional for every other active
        # segment. CaptionState has already guaranteed that the incoming
        # revision is newer than queued revisions of its own segment.
        latest_provisional: dict[int, tuple[int, int | None]] = {}
        for index, item in enumerate(self._pending):
            if item.segment is None or item.final or item.segment in queued_finals:
                continue
            if item.segment == incoming.segment:
                continue

            previous = latest_provisional.get(item.segment)
            if previous is None:
                latest_provisional[item.segment] = (index, item.revision)
                continue

            previous_revision = previous[1]
            if item.revision is not None and (previous_revision is None or item.revision >= previous_revision):
                latest_provisional[item.segment] = (index, item.revision)

        compacted: deque[PendingMessage] = deque()
        removed = 0

        for index, item in enumerate(self._pending):
            keep = (
                item.segment is None
                or item.final
                or (
                    item.segment != incoming.segment
                    and item.segment not in queued_finals
                    and latest_provisional.get(item.segment, (-1, None))[0] == index
                )
            )

            if keep:
                compacted.append(item)
            else:
                removed += 1

        self._pending = compacted
        self.coalesced_count += removed

    def _overflow(self) -> None:
        if self._stopped:
            return

        self.overflowed = True
        self._stopped = True
        self._available.set()

        # Close only this overloaded client rather than dropping durable state or growing memory without bound.
        asyncio.create_task(self.ws.close(code=1013, reason="client delivery queue saturated"))

    async def send_loop(self) -> None:
        try:
            while not self._stopped:
                if not self._pending:
                    self._available.clear()
                    await self._available.wait()
                    continue

                item = self._pending.popleft()
                await self.ws.send(item.payload)
                self.sent_count += 1
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

