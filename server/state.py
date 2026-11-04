# Details about the caption being sent by the caption source
import math
from typing import Any, Callable
from server.protocol import CaptionUpdateMessage

class CaptionSegment:
    def __init__(self, session:str, segment:int, revision:int, source_ts:float, final:bool, text:str):
        self.session = session
        self.segment_id = segment
        self.revision = revision
        self.source_ts = source_ts
        self.final = final
        self.text = text

    def to_dict(self) -> CaptionUpdateMessage:
        return {
            "type": "CAPTION_UPDATE",
            "session": self.session,
            "segment": self.segment_id,
            "revision": self.revision,
            "source_ts": self.source_ts,
            "final": self.final,
            "text": self.text
        }

class CaptionState:
    def __init__(self, session:str):
        self.session = session
        # Latest provisional caption for each active segment
        self.active: dict[int, CaptionSegment] = {}
        # Largest finalized segment ID
        self.highest_finalized_segment = 0

    def accept_update(self, message:dict[str, Any],
                      store_final: Callable[[CaptionSegment], None] | None = None) -> CaptionSegment | None:
        caption_update = self.parse_update(message)

        if caption_update is None:
            return None

        if caption_update.segment_id <= self.highest_finalized_segment:
            return None

        previous = self.active.get(caption_update.segment_id)

        if previous is not None and caption_update.revision <= previous.revision:
            return None

        if caption_update.final:
            # Store before committing state so capacity failures leave it retryable.
            if store_final is not None:
                store_final(caption_update)
            self.highest_finalized_segment = caption_update.segment_id
            self.active.pop(caption_update.segment_id, None)
        else:
            self.active[caption_update.segment_id] = caption_update

        return caption_update

    def parse_update(self, message:dict[str, Any]) -> CaptionSegment | None:
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

        return CaptionSegment(
            session=self.session,
            segment=segment,
            revision=revision,
            source_ts=source_ts,
            final=final,
            text=text
        )

