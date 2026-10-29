"""Independent delivery with congestion-triggered semantic backpressure."""
import asyncio
from collections import deque
from contextlib import suppress
import json
import time

from server.history import FinalHistory
from server.state import CaptionUpdate


class ClientDelivery:
    def __init__(self, ws, history: FinalHistory, history_items: list[dict], *,
                 max_pending=256, max_pending_bytes=1024 * 1024,
                 send_timeout=10.0, semantic_backpressure=True,
                 high_pending=32, low_pending=4,
                 high_bytes=128 * 1024, low_bytes=32 * 1024,
                 lag_seconds=0.25, slow_send_seconds=0.1,
                 recovery_seconds=0.5):
        self.ws = ws
        self.history = history
        # Captured synchronously with registration: finals already in HISTORY
        # must not be replayed as live updates.
        self.next_final = history.next_sequence
        self.initial_history = json.dumps({"type": "HISTORY", "items": history_items})
        self.pending = deque()
        self.pending_bytes = 0
        self.max_pending = max_pending
        self.max_pending_bytes = max_pending_bytes
        self.send_timeout = send_timeout
        self.ready = asyncio.Event()
        self.failure = None
        self.task = None
        self.stopped = False
        self.semantic_backpressure = semantic_backpressure
        self.high_pending = min(high_pending, max_pending)
        self.low_pending = min(low_pending, max(0, self.high_pending - 1))
        self.high_bytes = min(high_bytes, max_pending_bytes)
        self.low_bytes = min(low_bytes, max(0, self.high_bytes - 1))
        self.lag_seconds = lag_seconds
        self.slow_send_seconds = slow_send_seconds
        self.recovery_seconds = recovery_seconds
        self.congested = False
        self.last_pressure = 0.0
        self.send_started = None
        self.coalesced_count = 0
        self.congestion_count = 0
        self.recovery_count = 0

    def start(self):
        self.task = asyncio.create_task(self.run(), name="client-sender")

    def transport_bytes(self):
        """Only inspect public transport APIs; fake sockets may omit them."""
        transport = getattr(self.ws, "transport", None)
        return transport.get_write_buffer_size() if transport is not None else 0

    def enter_congestion(self, now):
        if not self.congested:
            self.congested = True
            self.congestion_count += 1
        self.last_pressure = now

    def compact(self):
        """Drop only unsent provisionals, never advance the final cursor."""
        latest = {}
        before = len(self.pending)
        for entry in self.pending:
            segment = entry[0]
            if segment > self.history.latest_segment:
                # Accepted source revisions arrive in increasing order.
                latest[segment] = entry
        self.pending = deque(latest.values())
        self.pending_bytes = sum(entry[2] for entry in self.pending)
        self.coalesced_count += before - len(self.pending)

    def update_pressure(self, now):
        if not self.semantic_backpressure:
            return
        oldest_age = now - self.pending[0][3] if self.pending else 0.0
        in_flight_age = now - self.send_started if self.send_started is not None else 0.0
        buffered = self.transport_bytes()
        final_lag = self.history.next_sequence - self.next_final
        pressure = (len(self.pending) >= self.high_pending or
                    self.pending_bytes >= self.high_bytes or
                    oldest_age >= self.lag_seconds or
                    in_flight_age >= self.slow_send_seconds or
                    buffered >= 32768 or final_lag >= 4)
        if pressure:
            self.enter_congestion(now)
        if self.congested:
            self.compact()
            # Separate high/low thresholds and a quiet interval avoid flapping.
            if (not pressure and len(self.pending) <= self.low_pending and
                    self.pending_bytes <= self.low_bytes and final_lag == 0 and
                    buffered <= 8192 and self.send_started is None and
                    now - self.last_pressure >= self.recovery_seconds):
                self.congested = False
                self.recovery_count += 1

    def offer(self, caption: CaptionUpdate, raw: str):
        """Never await a socket or queue space in the source handler."""
        if self.stopped or self.failure:
            return
        now = time.monotonic()
        self.update_pressure(now)
        if not caption.final:
            size = len(raw.encode("utf-8"))
            # Switch before crossing a hard limit, then replace obsolete work.
            if self.semantic_backpressure and (
                    len(self.pending) + 1 >= self.high_pending or
                    self.pending_bytes + size >= self.high_bytes):
                self.enter_congestion(now)
            if self.congested:
                self.compact()
                # The supplied source has one active segment, so replacement
                # makes room before appending even when the queue is full.
                retained = deque(e for e in self.pending if e[0] != caption.segment)
                self.coalesced_count += len(self.pending) - len(retained)
                self.pending = retained
                self.pending_bytes = sum(e[2] for e in retained)
            if (len(self.pending) >= self.max_pending or
                    self.pending_bytes + size > self.max_pending_bytes):
                self.failure = "Latest provisional exceeds client queue capacity"
            else:
                self.pending.append((caption.segment, raw, size, now))
                self.pending_bytes += size
        elif self.congested:
            # Final is already stored; its queued provisionals are obsolete.
            self.compact()
        self.ready.set()

    async def send(self, raw):
        started = time.monotonic()
        self.send_started = started
        try:
            await asyncio.wait_for(self.ws.send(raw), timeout=self.send_timeout)
        finally:
            self.send_started = None
        now = time.monotonic()
        if self.semantic_backpressure and now - started >= self.slow_send_seconds:
            self.enter_congestion(now)
            self.compact()

    async def run(self):
        try:
            await self.send(self.initial_history)
            self.initial_history = None
            while not self.stopped:
                if self.failure:
                    break
                self.update_pressure(time.monotonic())
                final = self.history.get_entry(self.next_final)
                # Preserve source order: same-segment provisionals before its
                # final; never send a later segment ahead of an earlier final.
                if self.pending and (final is None or
                        self.pending[0][0] <= final.caption.segment):
                    _, raw, size, _ = self.pending.popleft()
                    self.pending_bytes -= size
                    await self.send(raw)
                elif final is not None:
                    await self.send(final.raw)
                    self.next_final += 1
                else:
                    # No await between inspecting work and clearing the event.
                    self.ready.clear()
                    await self.ready.wait()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.failure = str(exc) or type(exc).__name__
        finally:
            self.stopped = True
            self.pending.clear()
            self.pending_bytes = 0
            self.initial_history = None
            # Closing wakes the connection handler even when the sender failed.
            with suppress(Exception):
                await self.ws.close(code=1013 if self.failure else 1000,
                                    reason=(self.failure or "Client disconnected").encode("utf-8")[:120].decode("utf-8", errors="ignore"))

    async def close(self):
        self.stopped = True
        if self.task is not None:
            if not self.task.done():
                self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task
