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
    """Track the active segment (provisional only), highest finalised segment and accepted & rejected count for testing"""
    def __init__(self, session:str):
        self.session = session
        self.active: dict[int, CaptionSegment] = {} # Latest provisional caption for each active segment
        self.highest_finalized_segment = 0 # Largest finalized segment ID
        self.accepted_count = 0
        self.rejected_count = 0

    def accept_update(self, message:dict[str, Any],
                      store_final: Callable[[CaptionSegment], None] | None = None) -> CaptionSegment | None:
        """Parse the source update, check if the source update is valid, update the final history and update the
        caption state (self.active, self.highest_finalized_segment).
        
        If new segment is final, then store it in history before committing the state so that when
        capacity failure, client will still make the new segment retryable because it is already inside
        final history."""
        
        caption_update = self.parse_update(message) # parse the raw message and return a CaptionSegment object

        if caption_update is None:
            self.rejected_count += 1
            return None

        if caption_update.segment_id <= self.highest_finalized_segment:
            self.rejected_count += 1
            return None

        previous = self.active.get(caption_update.segment_id)

        if previous and caption_update.revision <= previous.revision:
            self.rejected_count += 1
            return None

        if caption_update.final:
            # Store before committing state so capacity failures leave it retryable.
            store_final(caption_update)
            self.highest_finalized_segment = caption_update.segment_id # commit state
            self.active.pop(caption_update.segment_id, None) # commit state
        else:
            # if not final, then set the latest active provisional segment
            self.active[caption_update.segment_id] = caption_update

        self.accepted_count += 1
        return caption_update

    def parse_update(self, message:dict[str, Any]) -> CaptionSegment | None:
        """Parse the message dict object into **CaptionSegment** object"""

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
    