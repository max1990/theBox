"""
Bearing Normalization Utilities
==============================

Standardized functions for normalizing bearings to bow-relative coordinates
across all TheBox plugins. All bearings are normalized to [0, 360) degrees
with 0° = bow (forward direction).

This module provides:
- Bearing normalization functions
- Coordinate system conversions
- Validation utilities
- Common bearing operations
"""

import math
from typing import Literal, Tuple


def normalize_bearing_deg(bearing: float) -> float:
    """
    Normalize a bearing to [0, 360) degrees.
    
    Args:
        bearing: Bearing in degrees (can be any value)
        
    Returns:
        Normalized bearing in [0, 360) degrees
    """
    return (bearing % 360.0 + 360.0) % 360.0


def normalize_bearing_rad(bearing: float) -> float:
    """
    Normalize a bearing to [0, 2π) radians.
    
    Args:
        bearing: Bearing in radians (can be any value)
        
    Returns:
        Normalized bearing in [0, 2π) radians
    """
    return (bearing % (2 * math.pi) + 2 * math.pi) % (2 * math.pi)


def deg_to_rad(degrees: float) -> float:
    """Convert degrees to radians"""
    return math.radians(degrees)


def rad_to_deg(radians: float) -> float:
    """Convert radians to degrees"""
    return math.degrees(radians)


def apply_bow_offset(bearing_deg: float, bow_offset_deg: float) -> float:
    """
    Apply bow offset to a bearing.
    
    Args:
        bearing_deg: Bearing in degrees
        bow_offset_deg: Bow offset in degrees
        
    Returns:
        Bearing with bow offset applied and normalized
    """
    return normalize_bearing_deg(bearing_deg + bow_offset_deg)


def apply_sensor_offset(bearing_deg: float, sensor_offset_deg: float) -> float:
    """
    Apply sensor-specific offset to a bearing.
    
    Args:
        bearing_deg: Bearing in degrees
        sensor_offset_deg: Sensor offset in degrees
        
    Returns:
        Bearing with sensor offset applied and normalized
    """
    return normalize_bearing_deg(bearing_deg + sensor_offset_deg)


def convert_relative_to_bow(
    relative_bearing_deg: float,
    sensor_heading_deg: float,
    zero_axis: Literal["forward", "right", "left", "rear"] = "forward",
    positive_direction: Literal["clockwise", "counter_clockwise"] = "clockwise"
) -> float:
    """
    Convert sensor-relative bearing to bow-relative bearing.
    
    Args:
        relative_bearing_deg: Bearing relative to sensor (degrees)
        sensor_heading_deg: Sensor heading in degrees TRUE
        zero_axis: Zero reference axis ("forward", "right", "left", "rear")
        positive_direction: Positive direction ("clockwise", "counter_clockwise")
        
    Returns:
        Bow-relative bearing in degrees TRUE
    """
    # Apply positive direction
    if positive_direction == "counter_clockwise":
        relative_bearing_deg = -relative_bearing_deg
    
    # Apply zero axis offset
    if zero_axis == "right":
        relative_bearing_deg += 90.0
    elif zero_axis == "left":
        relative_bearing_deg -= 90.0
    elif zero_axis == "rear":
        relative_bearing_deg += 180.0
    
    # Add sensor heading and normalize
    return normalize_bearing_deg(sensor_heading_deg + relative_bearing_deg)


def convert_bow_to_relative(
    bow_bearing_deg: float,
    sensor_heading_deg: float,
    zero_axis: Literal["forward", "right", "left", "rear"] = "forward",
    positive_direction: Literal["clockwise", "counter_clockwise"] = "clockwise"
) -> float:
    """
    Convert bow-relative bearing to sensor-relative bearing.
    
    Args:
        bow_bearing_deg: Bow-relative bearing in degrees TRUE
        sensor_heading_deg: Sensor heading in degrees TRUE
        zero_axis: Zero reference axis ("forward", "right", "left", "rear")
        positive_direction: Positive direction ("clockwise", "counter_clockwise")
        
    Returns:
        Sensor-relative bearing in degrees
    """
    # Subtract sensor heading
    relative_bearing = normalize_bearing_deg(bow_bearing_deg - sensor_heading_deg)
    
    # Apply zero axis offset (reverse of convert_relative_to_bow)
    if zero_axis == "right":
        relative_bearing -= 90.0
    elif zero_axis == "left":
        relative_bearing += 90.0
    elif zero_axis == "rear":
        relative_bearing -= 180.0
    
    # Apply positive direction (reverse)
    if positive_direction == "counter_clockwise":
        relative_bearing = -relative_bearing
    
    return normalize_bearing_deg(relative_bearing)


def bearing_difference(bearing1_deg: float, bearing2_deg: float) -> float:
    """
    Calculate the shortest angular difference between two bearings.
    
    Args:
        bearing1_deg: First bearing in degrees
        bearing2_deg: Second bearing in degrees
        
    Returns:
        Angular difference in degrees [-180, 180]
    """
    diff = normalize_bearing_deg(bearing2_deg - bearing1_deg)
    if diff > 180.0:
        diff -= 360.0
    return diff


def bearing_average(bearings: list[float], weights: list[float] | None = None) -> float:
    """
    Calculate weighted average of bearings, handling wraparound.
    
    Args:
        bearings: List of bearings in degrees
        weights: Optional list of weights (default: equal weights)
        
    Returns:
        Average bearing in degrees [0, 360)
    """
    if not bearings:
        raise ValueError("Cannot average empty list of bearings")
    
    if weights is None:
        weights = [1.0] * len(bearings)
    
    if len(bearings) != len(weights):
        raise ValueError("Bearings and weights must have same length")
    
    # Convert to unit vectors
    x_sum = 0.0
    y_sum = 0.0
    total_weight = 0.0
    
    for bearing, weight in zip(bearings, weights, strict=True):
        x_sum += weight * math.cos(deg_to_rad(bearing))
        y_sum += weight * math.sin(deg_to_rad(bearing))
        total_weight += weight
    
    if total_weight == 0:
        raise ValueError("Total weight cannot be zero")
    
    # Convert back to bearing
    avg_rad = math.atan2(y_sum, x_sum)
    return normalize_bearing_deg(rad_to_deg(avg_rad))


def validate_bearing(bearing: float, min_deg: float = 0.0, max_deg: float = 360.0) -> bool:
    """
    Validate that a bearing is within expected range.
    
    Args:
        bearing: Bearing to validate
        min_deg: Minimum valid bearing (default: 0.0)
        max_deg: Maximum valid bearing (default: 360.0)
        
    Returns:
        True if bearing is valid
    """
    return min_deg <= bearing < max_deg


def clamp_bearing(bearing: float, min_deg: float = 0.0, max_deg: float = 360.0) -> float:
    """
    Clamp a bearing to valid range and normalize.
    
    Args:
        bearing: Bearing to clamp
        min_deg: Minimum valid bearing (default: 0.0)
        max_deg: Maximum valid bearing (default: 360.0)
        
    Returns:
        Clamped and normalized bearing
    """
    # First normalize to [0, 360)
    normalized = normalize_bearing_deg(bearing)
    
    # Then clamp to range
    if normalized < min_deg:
        return min_deg
    elif normalized >= max_deg:
        return max_deg - 0.001  # Just under max to avoid wraparound
    else:
        return normalized


def bearing_to_cardinal(bearing_deg: float) -> str:
    """
    Convert bearing to cardinal direction.
    
    Args:
        bearing_deg: Bearing in degrees
        
    Returns:
        Cardinal direction string
    """
    normalized = normalize_bearing_deg(bearing_deg)
    
    if 337.5 <= normalized or normalized < 22.5:
        return "N"
    elif 22.5 <= normalized < 67.5:
        return "NE"
    elif 67.5 <= normalized < 112.5:
        return "E"
    elif 112.5 <= normalized < 157.5:
        return "SE"
    elif 157.5 <= normalized < 202.5:
        return "S"
    elif 202.5 <= normalized < 247.5:
        return "SW"
    elif 247.5 <= normalized < 292.5:
        return "W"
    elif 292.5 <= normalized < 337.5:
        return "NW"
    else:
        return "N"  # Fallback


def cardinal_to_bearing(cardinal: str) -> float:
    """
    Convert cardinal direction to bearing.
    
    Args:
        cardinal: Cardinal direction (N, NE, E, SE, S, SW, W, NW)
        
    Returns:
        Bearing in degrees
    """
    cardinal_map = {
        "N": 0.0,
        "NE": 45.0,
        "E": 90.0,
        "SE": 135.0,
        "S": 180.0,
        "SW": 225.0,
        "W": 270.0,
        "NW": 315.0,
    }
    
    return cardinal_map.get(cardinal.upper(), 0.0)


def bearing_uncertainty_deg(
    base_uncertainty_deg: float,
    signal_strength: float | None = None,
    distance_km: float | None = None,
    visibility_km: float | None = None
) -> float:
    """
    Calculate bearing uncertainty based on environmental factors.
    
    Args:
        base_uncertainty_deg: Base uncertainty in degrees
        signal_strength: Signal strength (0-1, higher is better)
        distance_km: Distance in kilometers
        visibility_km: Visibility in kilometers
        
    Returns:
        Adjusted uncertainty in degrees
    """
    uncertainty = base_uncertainty_deg
    
    # Adjust for signal strength
    if signal_strength is not None:
        # Poor signal increases uncertainty
        signal_factor = max(0.5, 1.0 - signal_strength)
        uncertainty *= signal_factor
    
    # Adjust for distance
    if distance_km is not None:
        # Far targets have higher uncertainty
        distance_factor = 1.0 + (distance_km / 10.0)  # 10% increase per km
        uncertainty *= distance_factor
    
    # Adjust for visibility
    if visibility_km is not None:
        # Poor visibility increases uncertainty
        visibility_factor = max(0.5, visibility_km / 10.0)  # Assume 10km is good visibility
        uncertainty *= visibility_factor
    
    return max(0.1, uncertainty)  # Minimum uncertainty


def format_bearing(bearing_deg: float, precision: int = 1) -> str:
    """
    Format bearing for display.
    
    Args:
        bearing_deg: Bearing in degrees
        precision: Decimal places for display
        
    Returns:
        Formatted bearing string
    """
    normalized = normalize_bearing_deg(bearing_deg)
    return f"{normalized:.{precision}f}°"


def parse_bearing(bearing_str: str) -> float:
    """
    Parse bearing from string (handles various formats).
    
    Args:
        bearing_str: Bearing string (e.g., "45.5", "45.5°", "N", "NE")
        
    Returns:
        Bearing in degrees
    """
    bearing_str = bearing_str.strip().upper()
    
    # Try cardinal direction first
    if bearing_str in ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]:
        return cardinal_to_bearing(bearing_str)
    
    # Remove degree symbol and parse as float
    bearing_str = bearing_str.replace("°", "").replace("DEG", "").replace("DEGREES", "")
    
    try:
        return float(bearing_str)
    except ValueError:
        raise ValueError(f"Could not parse bearing: {bearing_str}")


# Convenience functions for common operations
def to_bow_relative(
    sensor_bearing_deg: float,
    sensor_heading_deg: float,
    bow_offset_deg: float = 0.0,
    sensor_offset_deg: float = 0.0,
    **kwargs
) -> float:
    """
    Convert sensor bearing to bow-relative bearing with all offsets applied.
    
    Args:
        sensor_bearing_deg: Sensor-relative bearing
        sensor_heading_deg: Sensor heading in degrees TRUE
        bow_offset_deg: Global bow offset
        sensor_offset_deg: Sensor-specific offset
        **kwargs: Additional arguments for convert_relative_to_bow
        
    Returns:
        Bow-relative bearing in degrees TRUE
    """
    # Convert to bow-relative
    bow_bearing = convert_relative_to_bow(
        sensor_bearing_deg, sensor_heading_deg, **kwargs
    )
    
    # Apply sensor offset
    bow_bearing = apply_sensor_offset(bow_bearing, sensor_offset_deg)
    
    # Apply bow offset
    bow_bearing = apply_bow_offset(bow_bearing, bow_offset_deg)
    
    return bow_bearing


def from_bow_relative(
    bow_bearing_deg: float,
    sensor_heading_deg: float,
    bow_offset_deg: float = 0.0,
    sensor_offset_deg: float = 0.0,
    **kwargs
) -> float:
    """
    Convert bow-relative bearing to sensor-relative bearing with all offsets applied.
    
    Args:
        bow_bearing_deg: Bow-relative bearing in degrees TRUE
        sensor_heading_deg: Sensor heading in degrees TRUE
        bow_offset_deg: Global bow offset
        sensor_offset_deg: Sensor-specific offset
        **kwargs: Additional arguments for convert_bow_to_relative
        
    Returns:
        Sensor-relative bearing in degrees
    """
    # Remove bow offset
    bow_bearing = normalize_bearing_deg(bow_bearing_deg - bow_offset_deg)
    
    # Remove sensor offset
    bow_bearing = normalize_bearing_deg(bow_bearing - sensor_offset_deg)
    
    # Convert to sensor-relative
    return convert_bow_to_relative(bow_bearing, sensor_heading_deg, **kwargs)
