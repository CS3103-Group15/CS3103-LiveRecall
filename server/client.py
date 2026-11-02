"""Independent delivery with bounded provisional work and shared final history."""
from __future__ import annotations

import asyncio
from collections import deque
from contextlib import suppress
import time
from typing import Any

from server.history import FinalHistory


class PendingMessage:
    def __init__(self, payload: str, segment: int | None = None):
        self.payload = payload
        self.segment = segment
        self.size = len(payload.encode('utf-8'))
        self.enqueued_at = time.monotonic()


class Client:
    QUEUE_BYTES = 1024 * 1024
    PRESSURE_BYTES = 128 * 1024
    MAX_QUEUE_AGE = 0.25
    SLOW_SEND_SECONDS = 0.1
    SEND_TIMEOUT = 10.0
    RECOVERY_SECONDS = 0.5
    CONGESTED_INTERVAL = 1.0
    FINAL_BATCH_BYTES = 128 * 1024

    def __init__(self, ws: Any, client_id: Any, history: FinalHistory):
        self.ws = ws
        self.client_id = client_id
        self.history = history
        # Captured without awaiting between HISTORY snapshot and registration.
        self.next_final = history.next_sequence
        self._pending: deque[PendingMessage] = deque()
        self._pending_bytes = 0
        self._available = asyncio.Event()
        self._sender_task: asyncio.Task[None] | None = None
        self._stopped = False
        self._send_started: float | None = None
        self._probe_started: float | None = None
        self._best_rtt: float | None = None
        self._receiver_slow_until = 0.0
        self._next_delivery_at = 0.0
        self.congested = False
        self._last_pressure = 0.0
        self.failure: str | None = None

    def start(self) -> None:
        if self._sender_task is None:
            self._sender_task = asyncio.create_task(self.send_loop(), name=f'client-sender-{self.client_id}')

    def _transport_bytes(self) -> int:
        transport = getattr(self.ws, 'transport', None)
        return transport.get_write_buffer_size() if transport is not None else 0

    def _enter_congestion(self, now: float) -> None:
        self.congested = True
        self._last_pressure = now

    def _compact(self, replacing_segment: int | None = None) -> None:
        # Control messages stay in order. Finals never enter this queue.
        latest = {}
        for item in self._pending:
            if item.segment is not None:
                latest[item.segment] = item
        retained = deque(
            item for item in self._pending
            if item.segment is None or (
                item.segment > self.history.latest_segment
                and item.segment != replacing_segment
                and latest[item.segment] is item
            )
        )
        self._pending = retained
        self._pending_bytes = sum(item.size for item in retained)

    def _update_pressure(self) -> None:
        now = time.monotonic()
        oldest = now - self._pending[0].enqueued_at if self._pending else 0.0
        sending = now - self._send_started if self._send_started is not None else 0.0
        buffered = self._transport_bytes()
        final_lag = self.history.next_sequence - self.next_final
        pressure = (
            self._pending_bytes >= self.PRESSURE_BYTES
            or oldest >= self.MAX_QUEUE_AGE
            or sending >= self.SLOW_SEND_SECONDS
            or buffered >= 16 * 1024
            or final_lag >= 4
            or (self._best_rtt is not None and self._probe_started is not None
                and now - self._probe_started >= self._pong_threshold())
            or now < self._receiver_slow_until
        )
        if pressure:
            self._enter_congestion(now)
        if self.congested:
            self._compact()
            if (not pressure and self._pending_bytes <= 32 * 1024 and final_lag == 0
                    and buffered <= 4096 and self._send_started is None
                    and now - self._last_pressure >= self.RECOVERY_SECONDS):
                self.congested = False
                self._next_delivery_at = 0.0

    def _pong_threshold(self) -> float:
        # Account for ordinary network RTT; a consistently delayed network
        # isn't, on its own, evidence of a slow application reader.
        return max(self.SLOW_SEND_SECONDS, 4 * (self._best_rtt or 0.0))

    def _send_final_batch(self) -> tuple[str, int]:
        """Snapshot a bounded prefix of unsent finals, in sequence order."""
        entries = []
        size = 0
        sequence = self.next_final
        while True:
            entry = self.history.get_entry(sequence)
            if entry is None:
                break
            if entries and size + entry.size > self.FINAL_BATCH_BYTES:
                break
            entries.append(entry.raw)
            size += entry.size
            sequence += 1
        # Reuse the existing finalized-history envelope. The browser and
        # public clients already merge these items using revision deduplication.
        return '{"type":"HISTORY","items":[' + ','.join(entries) + ']}', sequence

    def append(self, payload: str, *, segment: int | None = None,
               revision: int | None = None, final: bool = False) -> bool:
        """Nonblocking source offer. Finals must already be in shared history."""
        if self._stopped:
            return False
        self._update_pressure()
        if not final:
            item = PendingMessage(payload, segment)
            if self._pending_bytes + item.size >= self.PRESSURE_BYTES:
                self._enter_congestion(time.monotonic())
            if self.congested:
                self._compact(replacing_segment=segment)
            if self._pending_bytes + item.size > self.QUEUE_BYTES:
                self._fail('client delivery queue saturated')
                return False
            self._pending.append(item)
            self._pending_bytes += item.size
        elif self.congested:
            self._compact()
        self._available.set()
        return True

    def _fail(self, reason: str) -> None:
        self.failure = reason
        self._stopped = True
        self._available.set()

    async def _send(self, payload: str) -> None:
        started = time.monotonic()
        self._send_started = started
        try:
            await asyncio.wait_for(self.ws.send(payload), timeout=self.SEND_TIMEOUT)
        finally:
            elapsed = time.monotonic() - started
            self._send_started = None
        if elapsed >= self.SLOW_SEND_SECONDS:
            self._enter_congestion(time.monotonic())
            self._compact()

        # send() can complete into OS buffers while the peer's application is
        # far behind. Fence each message with a ping so receive-side WebSocket
        # backpressure propagates before we enqueue more obsolete revisions.
        # A pong acknowledges protocol processing, not application rendering.
        probe_started = time.monotonic()
        self._probe_started = probe_started
        threshold = self._pong_threshold() if self._best_rtt is not None else self.SEND_TIMEOUT
        try:
            pong = await asyncio.wait_for(self.ws.ping(), timeout=self.SEND_TIMEOUT)
            try:
                await asyncio.wait_for(asyncio.shield(pong), timeout=threshold)
            except asyncio.TimeoutError:
                self._enter_congestion(time.monotonic())
                self._compact()
                await asyncio.wait_for(pong, timeout=self.SEND_TIMEOUT)
        finally:
            self._probe_started = None
        rtt = time.monotonic() - probe_started
        if rtt >= threshold:
            # Leave time to drain frames already held by the receiver. Don't
            # immediately switch back to full revisions on the first fast pong.
            self._receiver_slow_until = time.monotonic() + 4 * rtt
            self._enter_congestion(time.monotonic())
        if self._best_rtt is None or rtt < self._best_rtt:
            self._best_rtt = rtt
        if self.congested:
            self._next_delivery_at = time.monotonic() + self.CONGESTED_INTERVAL

    async def send_loop(self) -> None:
        try:
            while not self._stopped:
                self._update_pressure()
                if self.congested:
                    delay = self._next_delivery_at - time.monotonic()
                    if delay > 0:
                        # Source offers keep coalescing during this client's
                        # pause; finals accumulate in bounded shared history.
                        await asyncio.sleep(delay)
                        self._update_pressure()
                final = self.history.get_entry(self.next_final)
                # HISTORY first, provisionals before their own final, and
                # earlier finals before a later segment's provisionals.
                if self.congested and final is not None and not (
                        self._pending and self._pending[0].segment is None):
                    payload, next_final = self._send_final_batch()
                    await self._send(payload)
                    self.next_final = next_final
                elif self._pending and (self._pending[0].segment is None
                        or final is None
                        or self._pending[0].segment <= final.caption.segment):
                    item = self._pending.popleft()
                    self._pending_bytes -= item.size
                    await self._send(item.payload)
                elif final is not None:
                    await self._send(final.raw)
                    self.next_final += 1
                else:
                    self._available.clear()
                    await self._available.wait()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._fail(str(exc) or type(exc).__name__)
        finally:
            self._stopped = True
            self._pending.clear()
            self._pending_bytes = 0
            with suppress(Exception):
                await self.ws.close(code=1013 if self.failure else 1000,
                                    reason='delivery unavailable; reconnect for history' if self.failure else '')

    async def stop(self) -> None:
        self._stopped = True
        self._available.set()
        if self._sender_task is not None:
            self._sender_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._sender_task
