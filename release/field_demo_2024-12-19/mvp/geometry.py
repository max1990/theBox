"""
Geometry utilities for TheBox
Handles bearing normalization and offset application
"""

import math


def normalize_deg(x: float) -> float:
    """
    Normalize angle to [0, 360) degrees
    """
    while x < 0:
        x += 360
    while x >= 360:
        x -= 360
    return x


def apply_offsets(
    raw_bearing_deg: float, plugin_offset_deg: float, bow_zero_deg: float
) -> float:
    """
    Apply BOW_ZERO_DEG first, then per-plugin offsets, normalize [0,360)

    Args:
        raw_bearing_deg: Raw sensor bearing in degrees
        plugin_offset_deg: Plugin-specific offset in degrees
        bow_zero_deg: Global bow-zero offset in degrees

    Returns:
        Normalized bearing in [0, 360) degrees
    """
    # Apply bow-zero offset first
    adjusted = raw_bearing_deg + bow_zero_deg

    # Apply plugin-specific offset
    adjusted += plugin_offset_deg

    # Normalize to [0, 360)
    return normalize_deg(adjusted)


def deg_to_rad(deg: float) -> float:
    """Convert degrees to radians"""
    return deg * math.pi / 180.0


def rad_to_deg(rad: float) -> float:
    """Convert radians to degrees"""
    return rad * 180.0 / math.pi


def compute_roi_sector(
    bearing_deg: float, fov_deg: float, roi_half_deg: float
) -> tuple[float, float]:
    """
    Compute ROI sector bounds for vision processing

    Args:
        bearing_deg: Center bearing in degrees
        fov_deg: Field of view in degrees
        roi_half_deg: Half-width of ROI in degrees

    Returns:
        Tuple of (start_angle, end_angle) in degrees
    """
    # Use ROI half-width if FOV is unknown, otherwise use proportional
    if fov_deg <= 0:
        half_width = roi_half_deg
    else:
        # Proportional to FOV
        half_width = min(roi_half_deg, fov_deg / 4.0)

    start_angle = normalize_deg(bearing_deg - half_width)
    end_angle = normalize_deg(bearing_deg + half_width)

    return start_angle, end_angle
