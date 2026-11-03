"""One client connection, bounded outgoing work and semantic sender policy."""
from __future__ import annotations
import asyncio
from collections import deque
from contextlib import suppress
from dataclasses import dataclass
import json
import math
import time

from server.history import FinalHistory
from server.protocol import CaptionUpdateMessage
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from server.application import LiveRecallApplication


@dataclass(slots=True)
class QueueEntry:
    segment: int # segment id
    raw: str # json serialised caption ready to be sent
    size: int # number of bytes in raw
    enqueued_at: float # timestamp when the entry enter the queue - use to measure queueing delay


class ClientSession:
    def __init__(self, websocket, history: FinalHistory, history_items: list[dict], *,
                 client_id=None,
                 max_pending=256, max_pending_bytes=1024 * 1024,
                 send_timeout=10.0, semantic_backpressure=True,
                 high_pending=32, low_pending=4,
                 high_bytes=128 * 1024, low_bytes=32 * 1024,
                 lag_seconds=0.25, slow_send_seconds=0.1,
                 recovery_seconds=0.5, feedback_window=1,
                 max_feedback_window=8, max_feedback_bytes=64 * 1024,
                 max_provisional_delay=2.0):
        # Connection & identity
        self.client_id: int = client_id
        self.websocket = websocket
        self.stopped: bool = False # becomes True when session is shutting down or has closed. Prevents new updates from being accepted
        self.failure: str | None = None # None when session is healthy. If something fails, it stores the description of the error
        self.sender_task: asyncio.Task | None = None # the asyncio.Task running the sender_loop()

        # Final caption delivery
        self.history: FinalHistory = history
        # Captured synchronously with registration: finals already in HISTORY
        # must not be replayed as live updates.
        self.next_final = history.next_sequence # the client's next final to be sent
        self.initial_history: str = json.dumps(history.get_history_message_format(history_items))

        # Provisional outgoing queue
        self.outgoing_queue: deque[QueueEntry] = deque() # provisional queue (no final segment included)
        self.outgoing_bytes = 0 # provisional queue size in bytes
        self.max_pending = max_pending # the high ceiling for outgoing_queue before going into congestion mode
        self.max_pending_bytes = max_pending_bytes # the high ceiling (bytes) for outgoing_queue
        self.ready = asyncio.Event() # event to wake the sender_loop() when new work becomes available
        self.provisional_wait_started = None # time when the current congested provisional waiting period began. It prevents continual replacement from postponing delivery forever.
        self.max_provisional_delay = max_provisional_delay # max time a provisional may be held before it must be sent. Default 2 seconds

        # Sending configuration & state
        self.send_timeout = send_timeout # Max time allowed for a websocket send OR ping/pong operation. Default 10 seconds
        self.send_started: float | None = None # Timestamp set while a send operation is running. `None` when no send is in progress. This allows the session to calculate (in_flight_age = now - self.send_started)
        self.slow_send_seconds: float = slow_send_seconds # Duration after which a websocket send is considered suspiciously slow. Default 0.1s
        self.slow_send_observations: int = 0 # number of consecutive slow send observed. 2 mildly slow send confirms congestions. 1 severely slow send can trigger congestion mode immediately!!!

        # Congestion config
        # queue reach high_pending -> enter_congestion() -> compact/coalesce provisionals 
        # -> queue drop below low_pending -> remain healthy for recovery_seconds -> return to normal mode
        self.semantic_backpressure = semantic_backpressure # enable/disable backpressure
        self.high_pending = min(high_pending, max_pending) # number of entry in the queue to enter congestion mode
        self.low_pending = min(low_pending, max(0, self.high_pending - 1)) # queue count minimum threshold before recovering from congestion
        self.high_bytes = min(high_bytes, max_pending_bytes) # queue byte size that cause congestion mode
        self.low_bytes = min(low_bytes, max(0, self.high_bytes - 1)) # queue byte size needed before recover
        self.lag_seconds = lag_seconds # Age threshold used to decide that queued, in-flight or feedback work is lagging
        self.recovery_seconds = recovery_seconds # required "quiet" period after the latest "pressure" before leaving congestion mode

        # Congestion runtime state
        self.congested = False # is congested mode?
        self.last_pressure = 0.0 # most recent monotonic time at which congestion pressure happen
        self.feedback_hold_until = 0.0 # Earliest time at which recovery is allowed after slow transport feedback
        self.coalesced_count = 0 # some metrics :)
        self.congestion_count = 0
        self.recovery_count = 0

        # Standard WebSocket control frames provide transport progress feedback
        # without changing the required caption protocol or client programs.
        if not 1 <= feedback_window <= max_feedback_window:
            raise ValueError("Feedback window must be positive and bounded")
        if max_feedback_bytes < 1:
            raise ValueError("Feedback byte limit must be positive")

        # Source update rate tracking -- to estimate how fast the source are coming in
        self.last_update_at = None
        self.update_interval = None

        # ping/pong transport feedback
        self.feedback_window: int = feedback_window # minimum number of sent message before requesting ping pong feedback. default 1.
                                               # the session initially checks transport progress after every sent message, 
                                               # once it knows the connection usual RTT, feedback_batch_size() may allow a bigger 
                                               # feedback window size
        self.max_feedback_window: int = max_feedback_window # max allowed dynamically calculated feedback batch size. default 8
        self.max_feedback_bytes: int = max_feedback_bytes # max bytes sent before forcing a pingpong checkpoint. default 64KB
        self.feedback_messages: int = 0 # number of message since the previous pingpong feedback checkpoint
        self.feedback_bytes: int = 0 # number of bytes sent since the previous pingpong feedback checkpoint
        self.feedback_started = None # time at which the pingpong feedback checkpoint started. None when no checkpoint is pending
        self.feedback_baseline = None # The best, lowest ping pong time observed for this client session connection
        self.feedback_checks = 0 # number of successful pingpong checkpoint
        self.feedback_delays = 0 # number of feedback checkpoints classfied as abnormally delayed
        self.slow_feedback_observations = 0 # number of consecutive delayed feedback observed

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
        """Returns number of bytes currently waiting in asyncio's local websocket transport write buffer.

        Only inspect public transport APIs; fake sockets may omit them."""
        transport = getattr(self.websocket, "transport", None)
        return transport.get_write_buffer_size() if transport is not None else 0

    def enter_congestion(self, now):
        """Set to congestion mode and update the `self.last_pressure`"""
        if not self.congested:
            self.congested = True
            self.congestion_count += 1
        self.last_pressure = now

    def compact(self):
        """Removes provisionals for segments that are already finalised. 
        
        For every still-active segment, keep only its newest queued revision. 
        Never advance the final cursor `self.next_history`."""
        latest = {}
        before = len(self.outgoing_queue)
        for entry in self.outgoing_queue:
            segment = entry.segment
            if segment > self.history.latest_segment_id:
                # Accepted source revisions arrive in increasing order.
                latest[segment] = entry
        self.outgoing_queue = deque(latest.values())
        self.outgoing_bytes = sum(entry.size for entry in self.outgoing_queue)
        self.coalesced_count += before - len(self.outgoing_queue)
        if not self.outgoing_queue:
            # No provisional remains, so no waiting period needs to be tracked.
            self.provisional_wait_started = None
        elif self.provisional_wait_started is None:
            # begin the waiting period at the oldest retained entry of the queue after compact.
            # This allows sender_loop() to enforce max_provisional_delay
            self.provisional_wait_started = min(entry.enqueued_at for entry in self.outgoing_queue)

    def update_pressure(self, now):
        """Decides whether the client is keeping up with the caption stream
        
        Gathers some congestion signals:
        - Unsent provisional queue size
        - Age of queued provisional updates
        - Duration of the current WebSocket send
        - Amount of bytes waiting in the local transport buffer
        - Number of finals the client is behind
        - Duration of an outstanding ping/pong checkpoint

        Then decide to either enter/remain in congestion mode OR leaves congestion mode after 
        client remained healthy for long enough
        """
        if not self.semantic_backpressure:
            return
        oldest_age = now - self.outgoing_queue[0].enqueued_at if self.outgoing_queue else 0.0 # the age of the oldest segment in the queue
        in_flight_age = now - self.send_started if self.send_started is not None else 0.0 # the age of the currently sending segment
        buffered = self.transport_bytes()
        final_lag = self.history.next_sequence - self.next_final # how many "final" the client is behind the latest final

        # slow ping pong feedback, becomes True when a ping/pong checkpoint is in progress && 
        # the connection already has a normal feedback baseline && 
        # the current ping/pong is taking longer than expected
        feedback_slow = (self.feedback_started is not None and
                         self.feedback_baseline is not None and
                         now - self.feedback_started >= max(
                             self.lag_seconds, self.feedback_threshold()))

        # is in pressure if:
        # feedback is slow OR
        # outgoing_queue exceed size OR
        # the oldest provisional age is too old OR
        # the segment that is currently being sent (in-flight) is being "sent" for too long OR
        # asyncio's local websocket transport write buffer exceed write_limit OR
        # client is more than 3 final behind
        pressure = (feedback_slow or len(self.outgoing_queue) >= self.high_pending or
                    self.outgoing_bytes >= self.high_bytes or
                    oldest_age >= self.lag_seconds or
                    in_flight_age >= max(self.lag_seconds, self.slow_send_seconds) or
                    buffered >= 32768 or final_lag >= 4)
        if pressure:
            self.enter_congestion(now)
        if self.congested:
            self.compact()
            # Separate high/low thresholds and a quiet interval avoid flapping.

            # recovery condition !!!
            if (not pressure and len(self.outgoing_queue) <= self.low_pending and
                    self.outgoing_bytes <= self.low_bytes and final_lag == 0 and
                    buffered <= 8192 and self.send_started is None and
                    now - self.last_pressure >= self.recovery_seconds and
                    now >= self.feedback_hold_until):
                self.congested = False
                self.recovery_count += 1

    def enqueue(self, message: CaptionUpdateMessage, raw: str | None = None) -> bool:
        """Offer a live caption update to client's sender

        This method is called by `DeliveryHub.publish()` after the application has
        accepted a source update. It performs only non-blocking, in-memory work;
        it never waits for queue space or sends data through the WebSocket.
        Consequently, a slow client cannot delay the source handler or other
        connected clients.

        Provisional updates are placed in this client's bounded outgoing queue.
        When the client is congested, obsolete provisional revisions are
        coalesced so that only the newest useful revision of an active segment is
        retained.

        Final updates are not copied into the per-client queue. They are already
        stored in the shared `FinalHistory` and are delivered by `sender_loop()`
        according to this client's `next_final` cursor. Receiving a final update
        wakes the sender and may remove provisional updates made obsolete by that
        final.

        Returns:
            True if the update was accepted for delivery or is available through
            FinalHistory. False if the client was already closed, had previously
            failed, or exceeded its bounded provisional queue capacity.
        """
        if self.stopped or self.failure:
            return False
        if raw is None:
            raw = json.dumps(message)
        now = time.monotonic()

        # estimate the source update rate. The sender uses this when choosing a
        # suitable transport-feedback window and provisional replacement delay.
        if self.last_update_at is not None:
            # Observe source cadence, not segment/revision counts or client IDs.
            interval = max(0.001, now - self.last_update_at)
            self.update_interval = (
                interval 
                if self.update_interval is None
                else 0.8 * self.update_interval + 0.2 * interval
            )
        self.last_update_at = now

        # re-evaluate whether the client is falling behind before accepting more proivisional segment
        self.update_pressure(now)

        # New caption is NOT final
        if not message["final"]:
            size = len(raw.encode("utf-8"))
            
            # Switch to congestion mode before crossing a hard limit, then replace obsolete work.
            if self.semantic_backpressure and (
                    len(self.outgoing_queue) + 1 >= self.high_pending or
                    self.outgoing_bytes + size >= self.high_bytes):
                self.enter_congestion(now)

            if self.congested:
                self.compact() # remove provisionals that are obsolete as there are finalised version of them
                # The supplied source has one active segment, so replacement
                # makes room before appending even when the queue is full.
                retained = deque(entry for entry in self.outgoing_queue # keep only the newest revision for this segment
                                 if entry.segment != message["segment"])
                
                self.coalesced_count += len(self.outgoing_queue) - len(retained) # useful metrics
                self.outgoing_queue = retained
                self.outgoing_bytes = sum(entry.size for entry in retained)

            # provisional queue is bounded by message count & byte size
            # If still out of queue bound, then fail
            # Else add the message into the queue
            if (len(self.outgoing_queue) >= self.max_pending or
                    self.outgoing_bytes + size > self.max_pending_bytes):
                self.failure = "Latest provisional exceeds client queue capacity"
            else:
                self.outgoing_queue.append(QueueEntry(message["segment"], raw, size, now))
                self.outgoing_bytes += size

                # Record when (time) a congested provisional first began waiting
                # This prevents it from being held indefinitely for further replacement
                if self.congested and self.provisional_wait_started is None:
                    self.provisional_wait_started = now

        # New caption is FINAL and in congested mode, then just compact the provisional queue
        elif self.congested:
            # Final is already stored; its queued provisionals are obsolete.
            self.compact()

        # Wake sender_loop(), either provisional work was queued or a new final is
        # now available through FinalHistory
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
        duration = now - started
        if self.semantic_backpressure and duration >= self.slow_send_seconds:
            self.slow_send_observations += 1
            # A short scheduling spike is not sustained backpressure. Severe
            # lag acts immediately; two consecutive mild sends confirm it too.
            if duration >= self.lag_seconds or self.slow_send_observations >= 2:
                self.enter_congestion(now)
                self.compact()
        else:
            self.slow_send_observations = 0
        await self.delivery_checkpoint(len(raw.encode("utf-8")))

    def feedback_threshold(self):
        # Compare against this connection's best RTT: ordinary propagation
        # delay alone shouldn't permanently classify a link as overloaded.
        return max(self.slow_send_seconds, 4 * (self.feedback_baseline or 0.0))

    def feedback_batch_size(self):
        """Bounded pipeline sized to baseline RTT and accepted update cadence."""
        if self.feedback_baseline is None:
            return self.feedback_window
        interval = self.update_interval or self.lag_seconds
        # Fast links retain one-message feedback. A propagation RTT longer than
        # the source spacing needs a small pipeline to avoid stop-and-wait lag.
        needed = math.ceil(2 * self.feedback_baseline / interval)
        return max(self.feedback_window, min(self.max_feedback_window, needed))

    async def delivery_checkpoint(self, size=0):
        if not self.semantic_backpressure or not callable(getattr(self.websocket, "ping", None)):
            return
        self.feedback_messages += 1
        self.feedback_bytes += size
        if (self.feedback_messages < self.feedback_batch_size() and
                self.feedback_bytes < self.max_feedback_bytes):
            return
        self.feedback_messages = 0
        self.feedback_bytes = 0
        started = time.monotonic()
        self.feedback_started = started
        try:
            pong = await asyncio.wait_for(self.websocket.ping(), timeout=self.send_timeout)
            await asyncio.wait_for(asyncio.shield(pong), timeout=self.send_timeout)
        finally:
            self.feedback_started = None
        elapsed = time.monotonic() - started
        self.feedback_checks += 1
        previous_baseline = self.feedback_baseline
        if previous_baseline is None:
            self.feedback_baseline = elapsed
        else:
            threshold = self.feedback_threshold()
            self.feedback_baseline = min(previous_baseline, elapsed)
            if elapsed >= threshold:
                self.feedback_delays += 1
                self.slow_feedback_observations += 1
                if elapsed >= self.lag_seconds or self.slow_feedback_observations >= 2:
                    now = time.monotonic()
                    self.enter_congestion(now)
                    # One fast pong doesn't establish sustained receive capacity.
                    self.feedback_hold_until = max(
                        self.feedback_hold_until,
                        now + min(60.0, max(self.recovery_seconds, 16 * elapsed)))
                    self.compact()
            else:
                self.slow_feedback_observations = 0

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
                        self.outgoing_queue[0].segment <= final.caption.segment_id):
                    if self.congested:
                        # Keep a brief replacement window for the latest
                        # provisional too. Otherwise fast transport feedback
                        # can release every new revision into a slow reader's
                        # buffers even while congestion mode is active.
                        now = time.monotonic()
                        quiet_window = max(self.lag_seconds, min(
                            1.0, 2 * (self.update_interval or 0.0)))
                        started = self.provisional_wait_started
                        if started is None:
                            started = self.outgoing_queue[0].enqueued_at
                        remaining = min(
                            quiet_window - (now - self.outgoing_queue[0].enqueued_at),
                            self.max_provisional_delay - (now - started))
                        if remaining > 0:
                            self.ready.clear()
                            try:
                                await asyncio.wait_for(self.ready.wait(), remaining)
                            except asyncio.TimeoutError:
                                pass
                            continue
                    entry = self.outgoing_queue.popleft()
                    self.outgoing_bytes -= entry.size
                    if not self.outgoing_queue:
                        self.provisional_wait_started = None
                    await self.send(entry.raw)
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
        self.provisional_wait_started = None
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
              f"feedback_checks={client.feedback_checks}; "
              f"feedback_delays={client.feedback_delays}; "
              f"failure={client.failure}", flush=True)