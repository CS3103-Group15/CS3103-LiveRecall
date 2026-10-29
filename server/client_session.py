"""One client connection, bounded outgoing work and semantic sender policy."""
from __future__ import annotations
import asyncio
from collections import deque
from contextlib import suppress
import json
import time

from server.history import FinalHistory
from server.protocol import CaptionUpdateMessage
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from server.application import LiveRecallApplication


class ClientSession:
    def __init__(self, websocket, history: FinalHistory, history_items: list[dict], *,
                 client_id=None,
                 max_pending=256, max_pending_bytes=1024 * 1024,
                 send_timeout=10.0, semantic_backpressure=True,
                 high_pending=32, low_pending=4,
                 high_bytes=128 * 1024, low_bytes=32 * 1024,
                 lag_seconds=0.25, slow_send_seconds=0.1,
                 recovery_seconds=0.5):
        self.client_id = client_id
        self.websocket = websocket
        self.history = history
        # Captured synchronously with registration: finals already in HISTORY
        # must not be replayed as live updates.
        self.next_final = history.next_sequence
        self.initial_history = json.dumps(history.get_history_message_format(history_items))
        self.outgoing_queue = deque()
        self.outgoing_bytes = 0
        self.max_pending = max_pending
        self.max_pending_bytes = max_pending_bytes
        self.send_timeout = send_timeout
        self.ready = asyncio.Event()
        self.failure = None
        self.sender_task = None
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

    @property
    def is_closed(self):
        return self.stopped

    def set_initial_history(self, history_items):
        """Called with application state protected, before the sender starts."""
        if self.sender_task is not None:
            raise RuntimeError("Cannot replace history after sender start")
        self.next_final = self.history.next_sequence
        self.initial_history = json.dumps(self.history.get_history_message_format(history_items))

    async def run(self):
        """Own connection lifetime while the independent sender does delivery."""
        self.start()
        try:
            async for _ in self.websocket:
                pass
        finally:
            await self.close()

    def start(self):
        self.sender_task = asyncio.create_task(self.sender_loop(), name=f"client-{self.client_id}-sender-task")

    def transport_bytes(self):
        """Only inspect public transport APIs; fake sockets may omit them."""
        transport = getattr(self.websocket, "transport", None)
        return transport.get_write_buffer_size() if transport is not None else 0

    def enter_congestion(self, now):
        if not self.congested:
            self.congested = True
            self.congestion_count += 1
        self.last_pressure = now

    def compact(self):
        """Drop only unsent provisionals, never advance the final cursor."""
        latest = {}
        before = len(self.outgoing_queue)
        for entry in self.outgoing_queue:
            segment = entry[0]
            if segment > self.history.latest_segment_id:
                # Accepted source revisions arrive in increasing order.
                latest[segment] = entry
        self.outgoing_queue = deque(latest.values())
        self.outgoing_bytes = sum(entry[2] for entry in self.outgoing_queue)
        self.coalesced_count += before - len(self.outgoing_queue)

    def update_pressure(self, now):
        if not self.semantic_backpressure:
            return
        oldest_age = now - self.outgoing_queue[0][3] if self.outgoing_queue else 0.0
        in_flight_age = now - self.send_started if self.send_started is not None else 0.0
        buffered = self.transport_bytes()
        final_lag = self.history.next_sequence - self.next_final
        pressure = (len(self.outgoing_queue) >= self.high_pending or
                    self.outgoing_bytes >= self.high_bytes or
                    oldest_age >= self.lag_seconds or
                    in_flight_age >= self.slow_send_seconds or
                    buffered >= 32768 or final_lag >= 4)
        if pressure:
            self.enter_congestion(now)
        if self.congested:
            self.compact()
            # Separate high/low thresholds and a quiet interval avoid flapping.
            if (not pressure and len(self.outgoing_queue) <= self.low_pending and
                    self.outgoing_bytes <= self.low_bytes and final_lag == 0 and
                    buffered <= 8192 and self.send_started is None and
                    now - self.last_pressure >= self.recovery_seconds):
                self.congested = False
                self.recovery_count += 1

    def enqueue(self, message: CaptionUpdateMessage, raw: str | None = None) -> bool:
        """Never await a socket or queue space in the source handler."""
        if self.stopped or self.failure:
            return False
        if raw is None:
            raw = json.dumps(message)
        now = time.monotonic()
        self.update_pressure(now)
        if not message["final"]:
            size = len(raw.encode("utf-8"))
            # Switch before crossing a hard limit, then replace obsolete work.
            if self.semantic_backpressure and (
                    len(self.outgoing_queue) + 1 >= self.high_pending or
                    self.outgoing_bytes + size >= self.high_bytes):
                self.enter_congestion(now)
            if self.congested:
                self.compact()
                # The supplied source has one active segment, so replacement
                # makes room before appending even when the queue is full.
                retained = deque(e for e in self.outgoing_queue if e[0] != message["segment"])
                self.coalesced_count += len(self.outgoing_queue) - len(retained)
                self.outgoing_queue = retained
                self.outgoing_bytes = sum(e[2] for e in retained)
            if (len(self.outgoing_queue) >= self.max_pending or
                    self.outgoing_bytes + size > self.max_pending_bytes):
                self.failure = "Latest provisional exceeds client queue capacity"
            else:
                self.outgoing_queue.append((message["segment"], raw, size, now))
                self.outgoing_bytes += size
        elif self.congested:
            # Final is already stored; its queued provisionals are obsolete.
            self.compact()
        self.ready.set()
        return self.failure is None

    async def send(self, raw):
        started = time.monotonic()
        self.send_started = started
        try:
            await asyncio.wait_for(self.websocket.send(raw), timeout=self.send_timeout)
        finally:
            self.send_started = None
        now = time.monotonic()
        if self.semantic_backpressure and now - started >= self.slow_send_seconds:
            self.enter_congestion(now)
            self.compact()

    async def sender_loop(self):
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
                if self.outgoing_queue and (final is None or
                        self.outgoing_queue[0][0] <= final.caption.segment_id):
                    _, raw, size, _ = self.outgoing_queue.popleft()
                    self.outgoing_bytes -= size
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
            await self.cleanup_connection()

    async def cleanup_connection(self):
        self.stopped = True
        self.outgoing_queue.clear()
        self.outgoing_bytes = 0
        self.initial_history = None
        reason = (self.failure or "Client disconnected").encode("utf-8")[:120]
        # Idempotent close also covers cancellation before the sender starts.
        with suppress(Exception):
            await self.websocket.close(
                code=1013 if self.failure else 1000,
                reason=reason.decode("utf-8", errors="ignore"))

    async def close(self):
        self.stopped = True
        if self.sender_task is not None:
            if not self.sender_task.done():
                self.sender_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.sender_task
        await self.cleanup_connection()


def parse_client_hello(hello:dict[str, Any]) -> tuple[int, int, int]:
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



async def handle_client(websocket, hello: dict[str, Any],
                        application: LiveRecallApplication) -> None:
    if hello.get("session") != "L1":
        await websocket.close(code=1008, reason="Invalid session")
        return
    client_id = hello.get("client_id")
    client = ClientSession(websocket, application.final_history, [], client_id=client_id,
                           semantic_backpressure=application.semantic_backpressure)
    try:
        await application.attach_client(client, *parse_client_hello(hello))
        print(f"client connected: id={client_id}; "
              f"clients={application.connected_client_count}", flush=True)
        await client.run()
    finally:
        await application.detach_client(client)
        print(f"client disconnected: id={client_id}; "
              f"clients={application.connected_client_count}; "
              f"congestion_entries={client.congestion_count}; "
              f"recoveries={client.recovery_count}; "
              f"coalesced={client.coalesced_count}; "
              f"failure={client.failure}", flush=True)
