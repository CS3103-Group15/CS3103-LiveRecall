"""Required WebSocket message shapes; wire field names remain unchanged."""
from typing import Literal, TypedDict


class CaptionUpdateMessage(TypedDict):
    type: Literal["CAPTION_UPDATE"]
    session: str
    segment: int
    revision: int
    source_ts: float
    final: bool
    text: str


class HistoryMessage(TypedDict):
    type: Literal["HISTORY"]
    items: list[CaptionUpdateMessage]
