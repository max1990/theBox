from dataclasses import dataclass


@dataclass
class SilvusConfig:
    """Minimal knobs. We keep conventions explicit so we can flip them once Silvus confirms."""

    # AoA convention (Silvus confirmed: positive = counter-clockwise)
    zero_axis: str = "forward"  # forward|right|left|rear
    positive: str = "ccw"  # cw|ccw

    # Policy
    default_bearing_error_deg: float = 5.0
    default_confidence: int = 75

    # Bring-up: optional path to a Silvus text log for auto-replay on load()
    replay_path: str | None = None

    # Status buffer size shown in the web UI
    status_buffer_max: int = 100
