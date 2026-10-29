from typing import TypedDict, Literal

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