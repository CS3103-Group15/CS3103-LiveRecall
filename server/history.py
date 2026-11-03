# How the server stores finalized caption segments for later retrieval by clients that have fallen behind
from collections import deque
import time
import json

from server.state import CaptionSegment
from server.protocol import CaptionUpdateMessage, HistoryMessage

class FinalEntry:
    def __init__(self, caption:CaptionSegment, stored_at:float, sequence:int):
        self.sequence = sequence
        self.raw = json.dumps(caption.to_dict())
        self.size = len(self.raw.encode("utf-8"))
        self.caption = caption
        self.stored_at = stored_at

class FinalHistory:
    def __init__(self, retention_seconds:float=70, max_bytes:int=32 * 1024 * 1024):
        self.retention_seconds = retention_seconds

        self.items:deque[FinalEntry] = deque()
        self.latest_segment_id = 0
        self.next_sequence = 0
        self.by_sequence: dict[int, FinalEntry] = {}
        self.max_bytes = max_bytes
        self.total_bytes = 0

    def add(self, caption:CaptionSegment) -> None:
        if caption.segment_id <= self.latest_segment_id:
            return

        now = time.monotonic()
        self.remove_old_entries()

        entry = FinalEntry(caption, now, self.next_sequence)
        if self.total_bytes + entry.size > self.max_bytes:
            raise OverflowError(
                "Final history capacity exhausted; "
                "required retention cannot be guaranteed"
            )

        self.items.append(entry)
        self.by_sequence[entry.sequence] = entry
        self.total_bytes += entry.size
        self.next_sequence += 1
        self.latest_segment_id = caption.segment_id

    def remove_old_entries(self, now:float|None=None) -> None:
        if now is None:
            now = time.monotonic()

        cutoff = now - self.retention_seconds

        while self.items and self.items[0].stored_at < cutoff:
            entry = self.items.popleft()
            self.by_sequence.pop(entry.sequence)
            self.total_bytes -= entry.size

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

    def get_entry(self, sequence: int) -> FinalEntry | None:
        """Read a sender bookmark; never silently skip expired finals."""
        self.remove_old_entries()
        if sequence < self.next_sequence and sequence not in self.by_sequence:
            raise LookupError("Client fell behind retained final history")
        return self.by_sequence.get(sequence)

    @staticmethod
    def get_history_message_format(history_items: list[CaptionUpdateMessage]) -> HistoryMessage:
        return {"type": "HISTORY", "items": history_items}
