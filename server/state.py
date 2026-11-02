import math
from typing import Any

class CaptionUpdate:
    def __init__(self, session:str, segment:int, revision:int, source_ts:float, final:bool, text:str):
        self.session = session
        self.segment = segment
        self.revision = revision
        self.source_ts = source_ts
        self.final = final
        self.text = text

    def to_dict(self) -> dict:
        return {
            "type": "CAPTION_UPDATE",
            "session": self.session,
            "segment": self.segment,
            "revision": self.revision,
            "source_ts": self.source_ts,
            "final": self.final,
            "text": self.text
        }

class CaptionState:
    def __init__(self, session:str):
        self.session = session
        self.active: dict[int, CaptionUpdate] = {} # Latest provisional caption for each active segment
        self.highest_finalized_segment = 0 # Largest finalized segment ID
        self.accepted_count = 0
        self.rejected_count = 0

    def accept_update(self, message:dict[str, Any], history) -> CaptionUpdate | None:
        caption_update = self.parse_update(message)

        if caption_update is None:
            self.rejected_count += 1
            return None

        if caption_update.segment <= self.highest_finalized_segment:
            self.rejected_count += 1
            return None

        previous = self.active.get(caption_update.segment)

        if previous is not None:
            if caption_update.revision <= previous.revision:
                self.rejected_count += 1
                return None

        if caption_update.final:
            # If storage overflows, leave finalized and active state unchanged.
            history.add(caption_update)
            self.highest_finalized_segment = caption_update.segment
            self.active.pop(caption_update.segment, None)
        else:
            self.active[caption_update.segment] = caption_update

        self.accepted_count += 1
        return caption_update

    def parse_update(self, message:dict[str, Any]) -> CaptionUpdate | None:
        if message.get("type") != "CAPTION_UPDATE":
            return None

        if message.get("session") != self.session:
            return None

        segment = message.get("segment")
        revision = message.get("revision")
        source_ts = message.get("source_ts")
        final = message.get("final")
        text = message.get("text")

        if type(segment) is not int or segment <= 0:
            return None

        if type(revision) is not int or revision <= 0:
            return None

        if type(final) is not bool:
            return None

        if not isinstance(text, str):
            return None

        if (
            isinstance(source_ts, bool)
            or not isinstance(source_ts, (int, float))
            or not math.isfinite(source_ts)
        ):
            return None

        return CaptionUpdate(
            session=self.session,
            segment=segment,
            revision=revision,
            source_ts=source_ts,
            final=final,
            text=text
        )
