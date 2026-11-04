from collections import deque
import time
import json

from server.state import CaptionSegment
from server.protocol import CaptionUpdateMessage

# One finalized caption stored in the shared history
class FinalEntry:
    def __init__(self, caption:CaptionSegment, stored_at:float, sequence:int):
        # Internal history position used by sender bookmarks, not the caption segment ID
        self.sequence = sequence
        # Serialize once so all client senders can reuse the same message
        self.raw = json.dumps(caption.to_dict())
        # Serialized message size used to enforce the history byte limit
        self.size = len(self.raw.encode("utf-8"))
        # Caption details used when preparing recovery history
        self.caption = caption
        # Time this final entered the server history, used for expiry
        self.stored_at = stored_at

# One bounded final-caption history shared by all clients
class FinalHistory:
    def __init__(self, retention_seconds:float=70, max_items:int=20000, max_bytes:int=32 * 1024 * 1024):
        # How long finals are retained after storage, default 70 seconds
        self.retention_seconds = retention_seconds
        # Maximum number of retained finals
        self.max_items = max_items

        # Finals in storage order, oldest first, so expired entries can be removed easily
        self.items:deque[FinalEntry] = deque()
        # Highest segment ID already stored as final
        self.latest_segment_id = 0
        # Internal sequence number to assign to the next stored final
        self.next_sequence = 0
        # Looks up a final directly using a sender's bookmark
        self.by_sequence: dict[int, FinalEntry] = {}
        # Maximum total serialized payload size retained in history
        self.max_bytes = max_bytes
        # Current total serialized payload size
        self.total_bytes = 0

    # Stores a new final while keeping history within its limits
    def add(self, caption:CaptionSegment) -> None:
        """Add new final segment into history and remove old entries
        
        Raises:
            OverflowError: If final history capacity is exhausted
        """
        if caption.segment_id <= self.latest_segment_id:
            return

        now = time.monotonic()
        self.remove_old_entries()

        entry = FinalEntry(caption, now, self.next_sequence)
        if len(self.items) >= self.max_items or self.total_bytes + entry.size > self.max_bytes:
            raise OverflowError(
                "Final history capacity exhausted; "
                "required retention cannot be guaranteed"
            )

        self.items.append(entry)
        self.by_sequence[entry.sequence] = entry
        self.total_bytes += entry.size
        self.next_sequence += 1
        self.latest_segment_id = caption.segment_id

    # Expires finals stored longer than the retention window
    def remove_old_entries(self, now:float|None=None) -> None:
        if now is None:
            now = time.monotonic()

        cutoff = now - self.retention_seconds

        while self.items and self.items[0].stored_at < cutoff:
            entry = self.items.popleft()
            self.by_sequence.pop(entry.sequence)
            self.total_bytes -= entry.size

    # Prepares missing recent finals for reconnecting or late-joining clients
    def get_recent(self, seconds:float, last_segment:int=0, last_revision:int=0) -> list[CaptionUpdateMessage]:
        self.remove_old_entries()
        cutoff = time.time() - seconds

        result = []

        for entry in self.items:
            caption = entry.caption

            if caption.source_ts < cutoff:
                continue

            if (caption.segment_id < last_segment or (caption.segment_id == last_segment and caption.revision <= last_revision)):
                continue

            result.append(caption.to_dict())

        return result

    def __len__(self) -> int:
        self.remove_old_entries()
        return len(self.items)

    # Finds the next final a client sender needs, using its delivery bookmark
    def get_entry(self, sequence: int) -> FinalEntry | None:
        """Get the history entry from the sequence number.
        
        Raises:
            LookupError: If the segment with sequence number doesn't exist/has been removed
            due to being too old.
        """
        self.remove_old_entries()
        if sequence < self.next_sequence and sequence not in self.by_sequence:
            raise LookupError("Client fell behind retained final history")
        return self.by_sequence.get(sequence)
