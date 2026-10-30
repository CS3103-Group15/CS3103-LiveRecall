from collections import deque
from collections.abc import Callable
from email import message
from enum import Enum, auto

from server.config import (
    CLIENT_QUEUE_HIGH_WATERMARK,
    CLIENT_QUEUE_LOW_WATERMARK,
    CLIENT_QUEUE_MAXSIZE,
)
from server.protocol import CaptionUpdateMessage


class AddResult(Enum):
    """Represent the action taken when trying to add a message into SemanticQueue"""
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
        low_watermark: int = CLIENT_QUEUE_LOW_WATERMARK
    ) -> None:
        # if not 0 <= low_watermark < high_watermark <= max_size:
        #     raise ValueError(
        #         "Require 0 <= low < high <= max_size"
        #     )

        self.max_size = max_size
        self.high_watermark = high_watermark
        self.low_watermark = low_watermark

        self.items: deque[CaptionUpdateMessage] = deque()

        self.coalesced_count = 0

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
        return message

    def add_normal(self, message: CaptionUpdateMessage) -> AddResult:
        """Retain every provisional during normal operation."""

        self.check_is_provisional(message)

        if self.size >= self.max_size: # safety net
            return AddResult.OVERFLOW

        self.items.append(message)
        return AddResult.ENQUEUED

    def add_coalesced(self, message: CaptionUpdateMessage, finalized_through_id: int) -> AddResult:
        """Keep only the newest useful provisional during congestion.
        
        Discard provisional segments with ID <= finalized_through_id (the most recent final ID) and
        discard provisional segment with same ID as message
        """

        self.check_is_provisional(message)

        removed_count = self.remove_finalized_through(finalized_through_id)

        removed_count += self.remove_segment_with_id(message["segment"])

        self.items.append(message)

        if removed_count > 0:
            return AddResult.COALESCED

        return AddResult.ENQUEUED

    def compact(self, finalized_through: int) -> int:
        """Compact all existing provisionals when congestion begins.
        
        Removes provisionals belonging to finalized segments and keeps only
        the latest queued revision of every unfinished segment.
        """

        original_size = self.size

        latest_index_by_segment: dict[int, int] = {}

        for index, message in enumerate(self.items):
            if message["segment"] > finalized_through:
                latest_index_by_segment[message["segment"]] = index # keep the latest revision of a segment

        self.items = deque(
            message
            for index, message in enumerate(self.items)
            if (
                message["segment"] > finalized_through
                and latest_index_by_segment[message["segment"]] == index
            )
        )

        removed_count = original_size - self.size
        self.coalesced_count += removed_count
        return removed_count



    def remove_segment_with_id(self, segment_id: int) -> int:
        original_size = self.size
        self.items = deque(
            message
            for message in self.items
            if message["segment"] != segment_id
        )
        removed_count = original_size - self.size
        self.coalesced_count += removed_count
        return removed_count

    def remove_finalized_through(self, segment_id: int) -> int:
        """Remove provisionals whose final now exists
        
        Remove all segments with id up to segment_id
        """

        original_size = self.size
        self.items = deque(
            message
            for message in self.items
            if message["segment"] > segment_id # final doesnt exist yet
        )
        removed_count = original_size - self.size
        self.coalesced_count += removed_count
        return removed_count
    

    def check_is_provisional(self, message: CaptionUpdateMessage) -> None:
        if message["final"]:
            raise ValueError(
                "Final captions must use shared FinalHistory"
            )


    # def add_message(
    #     self,
    #     message: CaptionUpdateMessage,
    # ) -> AddResult:
    #     """Add a provisional update without blocking."""

    #     if message["final"]:
    #         raise ValueError(
    #             "Final captions must use shared FinalHistory"
    #         )

    #     if not self.semantic_backpressure:
    #         if self.size >= self.max_size:
    #             return AddResult.OVERFLOW

    #         self.items.append(message)
    #         return AddResult.ENQUEUED

    #     if not self.congested:
    #         if self.size >= self.max_size:
    #             self.congested = True
    #             self.congestion_count += 1
    #         else:
    #             self.items.append(message)

    #             if self.size >= self.high_watermark: # if after adding, size > high_watermark -> set congested
    #                 self.congested = True
    #                 self.congestion_count += 1

    #             return AddResult.ENQUEUED

    #     # is in congested state: remove obsolete provisional revisions of the same
    #     # segment before adding the newest revision.
    #     removed_count = self._remove_matching(
    #         lambda queued: (
    #             queued["segment"] == message["segment"]
    #             and queued["final"] is False
    #         )
    #     )

    #     # If a different active segment filled the queue, 
    #     # remove one oldest provisional update to free up one space
    #     # without affecting user experience much
    #     if self.size >= self.max_size:
    #         if self._remove_oldest():
    #             removed_count += 1

    #     if self.size >= self.max_size: #safety net only
    #         return AddResult.OVERFLOW

    #     self.items.append(message)

    #     if removed_count > 0:
    #         self.coalesced_count += removed_count
    #         return AddResult.COALESCED

    #     return AddResult.ENQUEUED # in rare case where the queue got freed up mid-execution without removing any message

    # def _remove_matching(
    #     self,
    #     predicate: Callable[[CaptionUpdateMessage], bool],
    # ) -> int:
    #     original_size = self.size

    #     self.items = deque(
    #         message
    #         for message in self.items
    #         if not predicate(message)
    #     )

    #     return original_size - self.size

    # def _remove_oldest(self) -> bool:
    #     if not self.items:
    #         return False

    #     self.items.popleft()
    #     return True