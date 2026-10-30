from collections import deque
from collections.abc import Callable
from enum import Enum, auto

from server.config import (
    CLIENT_QUEUE_HIGH_WATERMARK,
    CLIENT_QUEUE_LOW_WATERMARK,
    CLIENT_QUEUE_MAXSIZE,
)
from server.protocol import CaptionUpdateMessage


class AddResult(Enum):
    ENQUEUED = auto()
    COALESCED = auto()
    OVERFLOW = auto()
    CLOSED = auto()


class SemanticQueue:
    """Bounded per-client queue for provisional updates."""

    def __init__(
        self,
        max_size: int = CLIENT_QUEUE_MAXSIZE,
        high_watermark: int = CLIENT_QUEUE_HIGH_WATERMARK,
        low_watermark: int = CLIENT_QUEUE_LOW_WATERMARK,
        *,
        semantic_backpressure: bool = True,
    ) -> None:
        if not 0 <= low_watermark < high_watermark <= max_size:
            raise ValueError(
                "Require 0 <= low < high <= max_size"
            )

        self.max_size = max_size
        self.high_watermark = high_watermark
        self.low_watermark = low_watermark
        self.semantic_backpressure = semantic_backpressure

        self.items: deque[CaptionUpdateMessage] = deque()
        self.congested = False

        self.coalesced_count = 0
        self.congestion_count = 0 # number of times client got into congestion state
        self.recovery_count = 0 # number of times client recovery from congestion

    @property
    def size(self) -> int:
        return len(self.items)

    def peek_message(self) -> CaptionUpdateMessage | None:
        if not self.items:
            return None

        return self.items[0]

    def pop_message(self) -> CaptionUpdateMessage | None:
        if not self.items:
            return None

        message = self.items.popleft()

        if self.congested and self.size <= self.low_watermark:
            self.congested = False
            self.recovery_count += 1

        return message

    def add_message(
        self,
        message: CaptionUpdateMessage,
    ) -> AddResult:
        """Add a provisional update without blocking."""

        if message["final"]:
            raise ValueError(
                "Final captions must use shared FinalHistory"
            )

        if not self.semantic_backpressure:
            if self.size >= self.max_size:
                return AddResult.OVERFLOW

            self.items.append(message)
            return AddResult.ENQUEUED

        if not self.congested:
            if self.size >= self.max_size:
                self.congested = True
                self.congestion_count += 1
            else:
                self.items.append(message)

                if self.size >= self.high_watermark: # if after adding, size > high_watermark -> set congested
                    self.congested = True
                    self.congestion_count += 1

                return AddResult.ENQUEUED

        # is in congested state: remove obsolete provisional revisions of the same
        # segment before adding the newest revision.
        removed_count = self._remove_matching(
            lambda queued: (
                queued["segment"] == message["segment"]
                and queued["final"] is False
            )
        )

        # If a different active segment filled the queue, 
        # remove one oldest provisional update to free up one space
        # without affecting user experience much
        if self.size >= self.max_size:
            if self._remove_oldest():
                removed_count += 1

        if self.size >= self.max_size: #safety net only
            return AddResult.OVERFLOW

        self.items.append(message)

        if removed_count > 0:
            self.coalesced_count += removed_count
            return AddResult.COALESCED

        return AddResult.ENQUEUED # in rare case where the queue got freed up mid-execution without removing any message

    def _remove_matching(
        self,
        predicate: Callable[[CaptionUpdateMessage], bool],
    ) -> int:
        original_size = self.size

        self.items = deque(
            message
            for message in self.items
            if not predicate(message)
        )

        return original_size - self.size

    def _remove_oldest(self) -> bool:
        if not self.items:
            return False

        self.items.popleft()
        return True