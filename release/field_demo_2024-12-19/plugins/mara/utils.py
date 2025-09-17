"""
Utility functions for MARA plugin.
"""

import structlog

logger = structlog.get_logger(__name__)


def normalize_angle(angle: float | str | None) -> float | None:
    """
    Normalize angle to 0-360 degrees.

    Args:
        angle: Angle in degrees (any range)

    Returns:
        Normalized angle in 0-360 range, or None if invalid
    """
    if angle is None:
        return None

    try:
        angle = float(angle)
        # Normalize to 0-360 range
        while angle < 0:
            angle += 360
        while angle >= 360:
            angle -= 360
        return angle
    except (ValueError, TypeError):
        return None


def clamp_value(
    value: float | str | None, min_val: float, max_val: float
) -> float | None:
    """
    Clamp value to specified range.

    Args:
        value: Value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Clamped value or None if invalid
    """
    if value is None:
        return None

    try:
        val = float(value)
        return max(min_val, min(max_val, val))
    except (ValueError, TypeError):
        return None


def convert_range_to_km(range_m: float | str | None) -> float | None:
    """
    Convert range from meters to kilometers.

    Args:
        range_m: Range in meters

    Returns:
        Range in kilometers or None if invalid
    """
    if range_m is None:
        return None

    try:
        range_val = float(range_m)
        # If range is > 1000, assume it's in meters and convert to km
        if range_val > 1000:
            return range_val / 1000.0
        return range_val
    except (ValueError, TypeError):
        return None


def parse_confidence(confidence: float | str | None) -> float | None:
    """
    Parse confidence value to 0.0-1.0 range.

    Args:
        confidence: Confidence value (0-1 or 0-100)

    Returns:
        Confidence in 0.0-1.0 range or None if invalid
    """
    if confidence is None:
        return None

    try:
        conf = float(confidence)
        # If confidence is > 1, assume it's a percentage
        if conf > 1.0:
            conf = conf / 100.0
        return max(0.0, min(1.0, conf))
    except (ValueError, TypeError):
        return None


def normalize_sensor_channel(channel: str | None) -> str:
    """
    Normalize sensor channel to standard values.

    Args:
        channel: Raw channel string

    Returns:
        Normalized channel: EO, IR, ACOUSTIC, or UNKNOWN
    """
    if not channel:
        return "UNKNOWN"

    channel = str(channel).upper().strip()

    if channel in ["EO", "ELECTRO-OPTICAL", "VISUAL", "CAMERA"]:
        return "EO"
    elif channel in ["IR", "INFRARED", "THERMAL"]:
        return "IR"
    elif channel in ["ACOUSTIC", "AUDIO", "SOUND", "MICROPHONE"]:
        return "ACOUSTIC"
    else:
        return "UNKNOWN"


def determine_event_type(raw_data: dict) -> str:
    """
    Determine event type from raw data.

    Args:
        raw_data: Raw MARA data dictionary

    Returns:
        Event type: DETECTION, TRACK, HEARTBEAT, or STATUS
    """
    # Check for explicit event type
    if "event_type" in raw_data:
        event_type = str(raw_data["event_type"]).upper()
        if event_type in ["DETECTION", "TRACK", "HEARTBEAT", "STATUS"]:
            return event_type

    # Check for heartbeat indicators
    raw_str = str(raw_data).lower()
    if "heartbeat" in raw_str or "status" in raw_str:
        return "HEARTBEAT"

    # Check for track indicators
    if "track_id" in raw_data or "track" in raw_str:
        return "TRACK"

    # Default to detection
    return "DETECTION"


def safe_float(value: float | str | None) -> float | None:
    """
    Safely convert value to float.

    Args:
        value: Value to convert

    Returns:
        Float value or None if conversion fails
    """
    if value is None:
        return None

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_int(value: int | str | None) -> int | None:
    """
    Safely convert value to int.

    Args:
        value: Value to convert

    Returns:
        Integer value or None if conversion fails
    """
    if value is None:
        return None

    try:
        return int(value)
    except (ValueError, TypeError):
        return None
