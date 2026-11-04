from dataclasses import dataclass


# Generates the settings constructor and prevents changes after initialization
@dataclass(frozen=True)
class DeliveryPolicy:
    """Queue bounds and congestion settings; fixed for a connection's lifetime."""
    # Hard limit on queued provisional entries for one client
    max_pending: int = 256
    # Hard limit on queued provisional payload bytes, default 1 MiB
    max_pending_bytes: int = 1024 * 1024
    # Maximum seconds for each caption-send, ping-write or pong-wait operation
    send_timeout: float = 10.0
    # Enables congestion handling and removal of obsolete provisional updates
    semantic_backpressure: bool = True
    # Queue entry count that triggers congestion before the hard limit
    high_pending: int = 32
    # Queue must shrink to this count or lower before congestion can clear
    low_pending: int = 4
    # Queued payload byte count that triggers congestion
    high_bytes: int = 128 * 1024
    # Queued bytes must fall to this level or lower before congestion can clear
    low_bytes: int = 32 * 1024
    # Queued-age pressure threshold; also the default severe-lag and minimum provisional-wait setting
    lag_seconds: float = 0.25
    # Mild slow-send threshold and minimum slow-pong threshold; repeated mild delays confirm congestion
    slow_send_seconds: float = 0.1
    # Minimum quiet period after the last pressure signal before congestion can clear
    recovery_seconds: float = 0.5
    # Starting and minimum message batch size before a ping/pong checkpoint
    feedback_window: int = 1
    # Maximum message batch size, even when RTT suggests a larger pipeline
    max_feedback_window: int = 8
    # Sent-byte threshold forcing a checkpoint; checked after each message
    max_feedback_bytes: int = 64 * 1024
    # Caps voluntary provisional waiting during congestion; network blocking can add more delay
    max_provisional_delay: float = 2.0

    # Runs after the generated constructor to validate and adjust related settings
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


# Each client gets its own mutable ping/pong progress values
@dataclass
class FeedbackState:
    bytes: int = 0
    messages: int = 0
    started: float | None = None
    baseline: float | None = None # the best observed ping/pong RTT
    hold_until: float = 0.0
