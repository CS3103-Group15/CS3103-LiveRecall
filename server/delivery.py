"""Stage 5: independent, bounded delivery; no provisional coalescing yet."""
import asyncio
from collections import deque
from contextlib import suppress
import json

from server.history import FinalHistory
from server.state import CaptionUpdate


class ClientDelivery:
    def __init__(self, ws, history: FinalHistory, history_items: list[dict], *,
                 max_pending=256, max_pending_bytes=1024 * 1024,
                 send_timeout=10.0):
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

    def start(self):
        self.task = asyncio.create_task(self.run(), name="client-sender")

    def offer(self, caption: CaptionUpdate, raw: str):
        """Never await a slow socket or a full queue in the source handler."""
        if self.stopped or self.failure:
            return
        if not caption.final:
            size = len(raw.encode("utf-8"))
            if (len(self.pending) >= self.max_pending or
                    self.pending_bytes + size > self.max_pending_bytes):
                self.failure = "Client pending queue capacity exceeded"
            else:
                self.pending.append((caption.segment, raw, size))
                self.pending_bytes += size
        # Finals remain in shared history; only the cursor is per client.
        self.ready.set()

    async def send(self, raw):
        await asyncio.wait_for(self.ws.send(raw), timeout=self.send_timeout)

    async def run(self):
        try:
            await self.send(self.initial_history)
            self.initial_history = None
            while not self.stopped:
                if self.failure:
                    break
                final = self.history.get_entry(self.next_final)
                # Preserve source order: same-segment provisionals before its
                # final; never send a later segment ahead of an earlier final.
                if self.pending and (final is None or
                        self.pending[0][0] <= final.caption.segment):
                    _, raw, size = self.pending.popleft()
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
