from collections import deque
import time
from typing import Final

from server.state import CaptionSegment, CaptionUpdateMessage
from server.protocol import HistoryMessage

class FinalEntry:
    """Stores the caption segment, stored_at time and sequence number of the entry."""

    def __init__(self, caption:CaptionSegment, stored_at:float, sequence: int):
        self.caption: CaptionSegment = caption
        self.stored_at: float = stored_at
        self.sequence = sequence

class FinalHistory:
    def __init__(self, retention_seconds:float=70, max_items:float=20000):
        self.retention_seconds = retention_seconds
        self.max_items = max_items

        self.items:deque[FinalEntry] = deque() # ordered (FIFO) storage of segments and size is bounded
        self.latest_segment_id = 0

        self.next_sequence = 0
        self.by_sequence: dict[int, FinalEntry] = {} # fast cursor lookup, size is also bounded

    def add(self, caption:CaptionSegment) -> None:
        """Add new finalized segment into history list and discard old entries"""

        # cant add segment that are older than the latest segment into the history
        if caption.segment_id <= self.latest_segment_id:
            return

        now = time.monotonic()
        self.remove_old_entries(now=now)

        if len(self.items) >= self.max_items:
            raise OverflowError(
                "Final history capacity exhausted; "
            )

        final_entry = FinalEntry(caption=caption, stored_at=now, sequence=self.next_sequence)

        self.items.append(final_entry)
        self.by_sequence[final_entry.sequence] = final_entry

        self.next_sequence += 1
        self.latest_segment_id = caption.segment_id

    def remove_old_entries(self, now:float|None=None) -> None:
        if now is None:
            now = time.monotonic()

        cutoff = now - self.retention_seconds

        while self.items and self.items[0].stored_at < cutoff:
            entry = self.items.popleft()
            self.by_sequence.pop(entry.sequence, None)

    def get_entry(self, sequence: int) -> FinalEntry | None:
        """Return the requested final with the sequence number.
        
        Returns:
            FinalEntry | None: The requested final caption entry if present, or
                None if the requested sequence has not been finalized yet.

        Raises:
            LookupError: If sequence < self.next_sequence and the entry is no
                longer in memory, indicating the client's read cursor fell behind
                the retained history buffer.
        """

        self.remove_old_entries()

        entry = self.by_sequence.get(sequence)

        if entry is not None:
            return entry

        if sequence < self.next_sequence:
            raise LookupError( # this will trigger disconnect of client in client_session.sender_loop()
                "Client fell behind retained final history"
            )

        return None

    def get_recent(self, seconds:float, last_segment:int=0, last_revision:int=0) -> list[CaptionUpdateMessage]:
        """Get the recent segments based on user client hello input
        
        Args:
            seconds (float): Number of seconds ago where client last connect
            last_segment (float): Last segment on client's side
            last_revision (int): Last revision on client's side
        """
        self.remove_old_entries()
        cutoff = time.time() - seconds

        result = []

        for entry in self.items:
            caption = entry.caption

            if caption.source_ts < cutoff:
                continue

            # only send segment that client already have
            # only resend same segment if the client's revision is older
            if (caption.segment_id < last_segment or (caption.segment_id == last_segment and caption.revision <= last_revision)):
                continue

            result.append(caption.to_dict())

        return result

    def get_history_message_format(self, history_items: list[CaptionUpdateMessage]) -> HistoryMessage:
        return {
            "type": "HISTORY",
            "items": history_items
        }

    def __len__(self) -> int:
        self.remove_old_entries()
        return len(self.items)
