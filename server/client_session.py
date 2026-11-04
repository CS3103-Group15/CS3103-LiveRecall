from __future__ import annotations
import asyncio
from collections import deque
from contextlib import suppress
from dataclasses import dataclass
import json
import math
import time

from server.delivery_policy import DeliveryPolicy, FeedbackState
from server.history import FinalHistory
from server.protocol import CaptionUpdateMessage, HistoryMessage
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from server.application import LiveRecallApplication


@dataclass(slots=True)
class QueueEntry:
    """One unsent provisional, with named fields instead of tuple positions."""
    segment: int # segment ID
    raw: str # json serialised caption ready to be sent
    size: int # number of bytes in raw
    enqueued_at: float # timestamp when the entry enter the queue - use to measure queueing delay


class ClientSession:
    def __init__(self, websocket, history: FinalHistory, history_items: list[dict], *,
                 policy: DeliveryPolicy | None = None, **policy_options):
        if policy is not None and policy_options:
            raise TypeError("Pass a policy or individual policy options, not both")
        self.policy = policy if policy is not None else DeliveryPolicy(**policy_options)
        # Tracks ping/pong timing and messages/bytes sent since the last checkpoint
        self.feedback = FeedbackState()
        # Connection used to send messages to this client
        self.websocket = websocket
        # Reference to shared final history
        self.history: FinalHistory = history
        # This client's pending provisional captions, waiting to be sent
        self.outgoing_queue: deque[QueueEntry] = deque()
        # Total size in bytes of provisionals currently in the queue
        self.outgoing_bytes: int = 0
        # Signal that wakes the sender when new work arrives.
        self.ready = asyncio.Event()
        # Stores a failure reason, if this session encounters an error
        self.failure: str | None = None
        # Holds the independent sender task once it starts
        self.sender_task: asyncio.Task | None = None
        # Prepares the initial HISTORY message and sets the next-final bookmark
        self.set_initial_history(history_items)
        # Whether this session has been stopped
        self.stopped: bool = False
        # Whether congestion mode is active for this client
        self.congested: bool = False
         # Time when congestion pressure was last detected
        self.last_pressure = 0.0
         # Start time of an ongoing caption send, `None` if not sending
        self.send_started: float | None = None
        # Smoothed time between caption arrivals
        self.update_interval: float | None = None
        # Previous caption arrival time
        self.last_update_at: float | None = None
        # When provisional deferral began
        self.provisional_wait_started: float | None = None
         # Counts consecutive mildly slow sends, capped at 2
        self.slow_send_observations: int = 0
        # Counts consecutive mildly slow ping/pong checks, capped at 2
        self.slow_feedback_observations: int = 0

    # Prepares the initial history snapshot for this client session's independent sender
    def set_initial_history(self, history_items):
        if self.sender_task is not None:
            raise RuntimeError("Cannot replace history after sender start")
        self.next_final = self.history.next_sequence
        message: HistoryMessage = {"type": "HISTORY", "items": history_items}
        self.initial_history = json.dumps(message)

    # Keeps the connection alive while the independent sender does delivery
    async def run(self):
        self.start()
        try:
            async for _ in self.websocket:
                pass
        finally:
            await self.close()

    # Starts this client's independent sender
    def start(self):
        self.sender_task = asyncio.create_task(self.sender_loop(), name="client-sender-task")

    def transport_bytes(self):
        """Returns number of bytes currently waiting in asyncio's local websocket transport write buffer.
        
        Only inspect public transport APIs; fake sockets may omit them.
        """
        transport = getattr(self.websocket, "transport", None)
        return transport.get_write_buffer_size() if transport is not None else 0

    def enter_congestion(self, now):
        """Set to congestion mode and update the `self.last_pressure`"""
        self.congested = True
        self.last_pressure = now

    # Removes provisionals for completed segments, keeps the latest unfinished revision
    def compact(self):
        """Removes provisionals for segments that are already finalised. 
        
        For every still-active segment, keep only its newest queued revision. 
        Never advance the final cursor `self.next_history`
        """
        latest = {}
        for entry in self.outgoing_queue:
            segment = entry.segment
            if segment > self.history.latest_segment_id:
                latest[segment] = entry
        self.outgoing_queue = deque(latest.values())
        self.outgoing_bytes = sum(entry.size for entry in self.outgoing_queue)
        if not self.outgoing_queue:
            # No provisional remains, so no waiting period needs to be tracked.
            self.provisional_wait_started = None
        elif self.provisional_wait_started is None:
            # begin the waiting period at the oldest retained entry of the queue after compact.
            # This allows sender_loop() to enforce max_provisional_delay
            self.provisional_wait_started = min(entry.enqueued_at for entry in self.outgoing_queue)

    # What signals congestion
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
        if not self.policy.semantic_backpressure:
            return
        oldest_age = now - self.outgoing_queue[0].enqueued_at if self.outgoing_queue else 0.0 # the age of the oldest segment in the queue
        in_flight_age = now - self.send_started if self.send_started is not None else 0.0 # the age of the currently sending segment
        buffered = self.transport_bytes()
        final_lag = self.history.next_sequence - self.next_final # how many "final" the client is behind the latest final

        # slow ping pong feedback, becomes True when a ping/pong checkpoint is in progress && 
        # the connection already has a normal feedback baseline && 
        # the current ping/pong is taking longer than expected
        feedback_slow = (self.feedback.started is not None and
                         self.feedback.baseline is not None and
                         now - self.feedback.started >= max(
                             self.policy.lag_seconds, self.feedback_threshold()))

        # Is in pressure if:
        # feedback is slow OR
        # outgoing_queue exceed size OR
        # the oldest provisional age is too old OR
        # the segment that is currently being sent (in-flight) is being "sent" for too long OR
        # asyncio's local websocket transport write buffer exceed write_limit OR
        # client is more than 3 final behind
        pressure = (feedback_slow or len(self.outgoing_queue) >= self.policy.high_pending or
                    self.outgoing_bytes >= self.policy.high_bytes or
                    oldest_age >= self.policy.lag_seconds or
                    in_flight_age >= max(self.policy.lag_seconds, self.policy.slow_send_seconds) or
                    buffered >= 32768 or final_lag >= 4)
        if pressure:
            self.enter_congestion(now)
        if self.congested:
            self.compact()
            # Separate high/low thresholds and a quiet interval avoid flapping.

            # recovery condition !!!
            if (not pressure and len(self.outgoing_queue) <= self.policy.low_pending and
                    self.outgoing_bytes <= self.policy.low_bytes and final_lag == 0 and
                    buffered <= 8192 and self.send_started is None and
                    now - self.last_pressure >= self.policy.recovery_seconds and
                    now >= self.feedback.hold_until):
                self.congested = False

    # For enqueuing a caption to the independent sender
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

        # Check if sender queue can still accept work
        if self.stopped or self.failure:
            return False
        if raw is None:
            raw = json.dumps(message)
        now = time.monotonic()

        # estimate the source update rate. The sender uses this when choosing a
        # suitable transport feedback window and provisional replacement delay.
        if self.last_update_at is not None:
            interval = max(0.001, now - self.last_update_at)
            self.update_interval = (
                interval 
                if self.update_interval is None
                else 0.8 * self.update_interval + 0.2 * interval
            )

        self.last_update_at = now

        # re-evaluate whether the client is in congestion before accepting more proivisional segment
        self.update_pressure(now)

        # New caption is NOT final
        if not message["final"]:
            size = len(raw.encode("utf-8"))

             # Switch to congestion mode before crossing a hard limit, then replace obsolete work.
            if self.policy.semantic_backpressure and (
                    len(self.outgoing_queue) + 1 >= self.policy.high_pending or
                    self.outgoing_bytes + size >= self.policy.high_bytes):
                self.enter_congestion(now)

            if self.congested:
                self.compact() # remove provisionals that are obsolete as there are finalised version of them

                # keep only the newest revision for this segment
                retained = deque(entry for entry in self.outgoing_queue
                                 if entry.segment != message["segment"])
                self.outgoing_queue = retained
                self.outgoing_bytes = sum(entry.size for entry in retained)

            # provisional queue is bounded by message count & byte size
            # If still out of queue bound, then fail
            # Else add the message into the queue
            if (len(self.outgoing_queue) >= self.policy.max_pending or
                    self.outgoing_bytes + size > self.policy.max_pending_bytes):
                self.failure = "Latest provisional exceeds client queue capacity"
            else:
                # Enqueue the latest provisional if it fits within the hard limits
                self.outgoing_queue.append(QueueEntry(message["segment"], raw, size, now))
                self.outgoing_bytes += size

                # Record when (time) a congested provisional first began waiting
                # This prevents it from being held indefinitely for further replacement
                if self.congested and self.provisional_wait_started is None:
                    self.provisional_wait_started = now

        # New caption is FINAL and in congested mode, then just compact the provisional queue
        elif self.congested:
            self.compact()

        # Wake sender_loop(), either provisional work was queued or a new final is
        # now available through FinalHistory
        self.ready.set()
        return self.failure is None

    # Sender sends caption to client
    async def send(self, raw):
        """Send one serialised message and observe delivery pressure
        
        After sending, measure the duration taken to send. One severely slow send or 2 consecutive mildly slow send
        will make the client enter congestion mode and trigger provisional queue compact. A normal send reset the 
        consecutive slow-send counter.

        Finally record the message in pingpong feedback so that transport progress can be check periodically.
        """
        started = time.monotonic()
        self.send_started = started
        try:
            await asyncio.wait_for(self.websocket.send(raw), timeout=self.policy.send_timeout) # attempts to send but limit to send_timeout
        finally:
            self.send_started = None
        now = time.monotonic()
        duration = now - started # amount of time taken to send one message
        # Checks if send took longer than expected and if is sustained
        if self.policy.semantic_backpressure and duration >= self.policy.slow_send_seconds:
            self.slow_send_observations = min(2, self.slow_send_observations + 1)

            # enter congestion if sending takes severely too long OR we have seen 2 consecutive mildly slow send
            if (duration >= max(self.policy.lag_seconds, self.policy.slow_send_seconds) or
                    self.slow_send_observations >= 2):
                self.enter_congestion(now)
                self.compact()
        else:
            self.slow_send_observations = 0 # no slow send, reset the consecutive slow send observation counter

        # Handles the ping/pong feedback mechanism
        await self.delivery_checkpoint(len(raw.encode("utf-8")))

    def feedback_threshold(self):
        """Calculate how slow a ping/pong response need to be before considered as unusual
        
        Returns the maximum of:
        - The fixed minimum delay `slow_send_seconds`
        - 4x the best observed ping/pong round-trip time `feedback.baseline`."""
        return max(self.policy.slow_send_seconds, 4 * (self.feedback.baseline or 0.0))

    def feedback_batch_size(self) -> int:
        """Calculate how many message can be send between ping/pong checkpoint"""
        if self.feedback.baseline is None: # before RTT baseline exist, use the configured starting batch size
            return self.policy.feedback_window

        # use the estimate time between caption updates. If estimate doesnt exist yet, fallback to `lag_second`
        interval = self.update_interval or self.policy.lag_seconds

        # needed batch size = ceil(2xbaseline / update_interval)
        # So that a high latency but healthy connection can send a small batch rather than waiting for pong for every message
        needed = math.ceil(2 * self.feedback.baseline / max(0.001, interval))

        # bound the result, prevents the dynamic batch size from being too small/too large
        return max(self.policy.feedback_window, min(self.policy.max_feedback_window, needed))

    # Checks if the client is able to receive more work using ping/pong feedback
    async def delivery_checkpoint(self, size=0) -> None:
        if not self.policy.semantic_backpressure or not callable(getattr(self.websocket, "ping", None)):
            return
        self.feedback.messages += 1
        self.feedback.bytes += size
        if (self.feedback.messages < self.feedback_batch_size() and
                self.feedback.bytes < self.policy.max_feedback_bytes):
            return

        # reset to 0 because we will wait until ping/pong checkpoint is reached
        self.feedback.messages = 0
        self.feedback.bytes = 0
        started = time.monotonic()
        self.feedback.started = started
        # Ping the client and wait for pong
        try:
            pong = await asyncio.wait_for(self.websocket.ping(), timeout=self.policy.send_timeout)
            await asyncio.wait_for(asyncio.shield(pong), timeout=self.policy.send_timeout)
        finally:
            self.feedback.started = None
        elapsed = time.monotonic() - started
        # Establish a baseline for ping/pong RTT
        previous_baseline = self.feedback.baseline
        if previous_baseline is None:
            self.feedback.baseline = elapsed
        else:
            threshold = self.feedback_threshold()
            self.feedback.baseline = min(previous_baseline, elapsed)
            # If RTT slow check if is sustained
            if elapsed >= threshold:
                self.slow_feedback_observations = min(2, self.slow_feedback_observations + 1)
                # Compact if congested by removing old provisionals
                if (elapsed >= max(self.policy.lag_seconds, threshold) or
                        self.slow_feedback_observations >= 2):
                    now = time.monotonic()
                    self.enter_congestion(now)
                    self.feedback.hold_until = max(
                        self.feedback.hold_until,
                        now + min(60.0, max(self.policy.recovery_seconds, 16 * elapsed)))
                    self.compact()
            else:
                self.slow_feedback_observations = 0

    # Independent sender loop, delivering queued work to the client
    async def sender_loop(self) -> None:
        """Send initial history, then keep sending provisional & final updates to one client
        
        Message ordering is based on segment IDs. A queued provisional is sent
        before a final when its segment ID is less than or equal to the next
        final's segment ID. Otherwise, the earlier final is sent first. Final
        captions are retrieved using the client's next_final history cursor,
        which is advanced only after the final has been sent successfully.

        During congestion, briefly defer a provisional to give a newer revision
        or final time to replace it. The delay ends when either the replacement
        quiet window or the maximum total provisional-deferral period expires.
        After every wait, recheck the queue and history because the available
        work may have changed.

        When no work is available, sleep on the ready event until enqueue() makes
        another update available. This avoids repeatedly checking an empty queue.
        """
        try:
            # Sends the initial history snapshot before any queued work
            await self.send(self.initial_history)
            self.initial_history = None
            # Checks for new work
            while not self.stopped:
                if self.failure:
                    break
                # Update congestion state and compact the queue if needed
                self.update_pressure(time.monotonic())
                final = self.history.get_entry(self.next_final)

                # Checks if is send a provisional
                if self.outgoing_queue and (final is None or
                        self.outgoing_queue[0].segment <= final.caption.segment_id):
                    if self.congested:
                        now = time.monotonic()
                        quiet_window = max(self.policy.lag_seconds, min(
                            1.0, 2 * (self.update_interval or 0.0)))
                        started = self.provisional_wait_started
                        if started is None:
                            started = self.outgoing_queue[0].enqueued_at
                        remaining = min(
                            quiet_window - (now - self.outgoing_queue[0].enqueued_at),
                            self.policy.max_provisional_delay - (now - started)
                        )
                        if remaining > 0:
                            self.ready.clear()
                            try:
                                await asyncio.wait_for(self.ready.wait(), remaining)
                            except asyncio.TimeoutError:
                                pass
                            continue

                    # Send provisional immediately in normal mode
                    # In congestion, send the latest retained provisional once remaining <= 0 [either quiet_window expires OR maximum total deferral period (max_provisional_delay) expires]
                    entry = self.outgoing_queue.popleft()
                    self.outgoing_bytes -= entry.size
                    if not self.outgoing_queue:
                        self.provisional_wait_started = None
                    await self.send(entry.raw)

                # Checks if is send a final
                elif final is not None:
                    await self.send(final.raw)
                    self.next_final += 1
                else:
                    # Sleep till new work arrives or connection closes
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


# Server's handler for a client connection
async def handle_client(websocket, hello: dict[str, Any],
                        application: LiveRecallApplication) -> None:
    if hello.get("session") != "L1":
        await websocket.close(code=1008, reason="Invalid session")
        return
    client_id = hello.get("client_id")
    # Creates an independent sender for each client
    client = ClientSession(websocket, application.final_history, [],
                           semantic_backpressure=application.semantic_backpressure)
    # Registers the client with the server and prepares the initial history snapshot for its independent sender
    try:
        await application.attach_client(client, *parse_client_hello(hello))
        print(f"client connected: id={client_id}; "
              f"clients={application.connected_client_count}", flush=True)
        await client.run()
    finally:
        await application.detach_client(client)
        print(f"client disconnected: id={client_id}; "
              f"clients={application.connected_client_count}; "
              f"failure={client.failure}", flush=True)
