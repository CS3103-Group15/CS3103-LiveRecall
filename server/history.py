from collections import deque
import time

from server.state import CaptionUpdate

class FinalEntry:
    def __init__(self, caption:CaptionUpdate, stored_at:float):
        self.caption = caption
        self.stored_at = stored_at

class FinalHistory:
    def __init__(self, retention_seconds:float=70, max_items:float=20000):
        self.retention_seconds = retention_seconds
        self.max_items = max_items

        self.items:deque[FinalEntry] = deque()
        self.latest_segment = 0

    def add(self, caption:CaptionUpdate) -> None:
        if caption.segment <= self.latest_segment:
            return

        now = time.monotonic()
        self.remove_old_entries()

        if len(self.items) >= self.max_items:
            raise OverflowError(
                "Final history capacity exhausted; "
                "required retention cannot be guaranteed"
            )

        self.items.append(
            FinalEntry(caption=caption, stored_at=now)
        )
        self.latest_segment = caption.segment

    def remove_old_entries(self, now:float|None=None) -> None:
        if now is None:
            now = time.monotonic()

        cutoff = now - self.retention_seconds

        while self.items and self.items[0].stored_at < cutoff:
            self.items.popleft()

    def get_recent(self, seconds:float, last_segment:int=0, last_revision:int=0) -> list[dict]:
        self.remove_old_entries()
        cutoff = time.time() - seconds

        result = []

        for entry in self.items:
            caption = entry.caption

            if caption.source_ts < cutoff:
                continue

            if (caption.segment < last_segment or (caption.segment == last_segment and caption.revision <= last_revision)):
                continue

            result.append(caption.to_dict())

        return result

    def __len__(self) -> int:
        self.remove_old_entries()
        return len(self.items)
