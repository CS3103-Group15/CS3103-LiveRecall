# START: Separate immutable delivery settings from mutable transport feedback.
from dataclasses import dataclass


@dataclass(frozen=True)
class DeliveryPolicy:
    """Queue bounds and congestion settings; fixed for a connection's lifetime."""
    max_pending: int = 256
    max_pending_bytes: int = 1024 * 1024
    send_timeout: float = 10.0
    semantic_backpressure: bool = True
    high_pending: int = 32
    low_pending: int = 4
    high_bytes: int = 128 * 1024
    low_bytes: int = 32 * 1024
    lag_seconds: float = 0.25
    slow_send_seconds: float = 0.1
    recovery_seconds: float = 0.5
    feedback_window: int = 1
    max_feedback_window: int = 8
    max_feedback_bytes: int = 64 * 1024
    max_provisional_delay: float = 2.0

    def __post_init__(self):
        if not 1 <= self.feedback_window <= self.max_feedback_window:
            raise ValueError("Feedback window must be positive and bounded")
        if self.max_feedback_bytes < 1:
            raise ValueError("Feedback byte limit must be positive")
        high_pending = min(self.high_pending, self.max_pending)
        high_bytes = min(self.high_bytes, self.max_pending_bytes)
        object.__setattr__(self, "high_pending", high_pending)
        object.__setattr__(self, "low_pending", min(self.low_pending, max(0, high_pending - 1)))
        object.__setattr__(self, "high_bytes", high_bytes)
        object.__setattr__(self, "low_bytes", min(self.low_bytes, max(0, high_bytes - 1)))


@dataclass
class FeedbackState:
    """Progress of the current bounded ping/pong delivery batch."""
    bytes: int = 0
    messages: int = 0
    started: float | None = None
    baseline: float | None = None
    hold_until: float = 0.0
# END: Separate immutable delivery settings from mutable transport feedback.
