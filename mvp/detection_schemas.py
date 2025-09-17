"""
Standardized Detection Schemas
==============================

Common schemas for all detection types across TheBox plugins.
All detections are normalized to bow-relative coordinates with
standardized field names and types.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


class BaseDetection(BaseModel):
    """Base class for all detections with common fields"""
    
    timestamp: datetime = Field(description="Detection timestamp (UTC)")
    source: str = Field(description="Detection source identifier")
    bearing_deg: float = Field(ge=0, lt=360, description="Bearing in degrees [0, 360)")
    confidence: float = Field(ge=0, le=1, description="Detection confidence [0, 1]")
    track_id: str = Field(description="Unique track identifier")
    
    # Optional common fields
    range_m: Optional[float] = Field(None, ge=0, description="Range in meters")
    altitude_m: Optional[float] = Field(None, description="Altitude in meters")
    speed_ms: Optional[float] = Field(None, ge=0, description="Speed in m/s")
    course_deg: Optional[float] = Field(None, ge=0, lt=360, description="Course in degrees")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator('bearing_deg', 'course_deg')
    @classmethod
    def normalize_angle(cls, v):
        """Normalize angles to [0, 360) degrees"""
        if v is None:
            return v
        return (v % 360.0 + 360.0) % 360.0


class RFDetection(BaseDetection):
    """RF-based detection (DroneShield, Silvus, etc.)"""
    
    source: Literal["droneshield", "silvus", "rf"] = Field(description="RF source type")
    frequency_mhz: Optional[float] = Field(None, ge=0, description="Frequency in MHz")
    rssi_dbm: Optional[float] = Field(None, description="RSSI in dBm")
    signal_bars: Optional[int] = Field(None, ge=0, le=10, description="Signal strength bars")
    protocol: Optional[str] = Field(None, description="RF protocol")
    device_name: Optional[str] = Field(None, description="Device name/model")
    
    # RF-specific metadata
    bandwidth_hz: Optional[float] = Field(None, ge=0, description="Signal bandwidth in Hz")
    modulation: Optional[str] = Field(None, description="Modulation type")
    snr_db: Optional[float] = Field(None, description="Signal-to-noise ratio in dB")


class VisionDetection(BaseDetection):
    """Vision-based detection (EO/IR cameras)"""
    
    source: Literal["vision", "eo", "ir", "trakka"] = Field(description="Vision source type")
    verified: bool = Field(description="Vision verification result")
    label: str = Field(description="Detected object label")
    bbox: Optional[tuple[float, float, float, float]] = Field(
        None, description="Bounding box (x1, y1, x2, y2) in pixels"
    )
    pixel_height: Optional[int] = Field(None, ge=0, description="Object height in pixels")
    frame_height: Optional[int] = Field(None, ge=0, description="Frame height in pixels")
    fov_deg: Optional[float] = Field(None, ge=0, le=180, description="Field of view in degrees")
    
    # Vision-specific metadata
    backlit: Optional[bool] = Field(None, description="Backlit conditions")
    poor_contrast: Optional[bool] = Field(None, description="Poor contrast conditions")
    tracker_id: Optional[str] = Field(None, description="Object tracker ID")
    latency_ms: Optional[int] = Field(None, ge=0, description="Processing latency in ms")


class AcousticDetection(BaseDetection):
    """Acoustic-based detection (MARA, etc.)"""
    
    source: Literal["mara", "acoustic"] = Field(description="Acoustic source type")
    spl_dba: Optional[float] = Field(None, description="Sound pressure level in dBA")
    frequency_hz: Optional[float] = Field(None, ge=0, description="Frequency in Hz")
    snr_db: Optional[float] = Field(None, description="Signal-to-noise ratio in dB")
    sea_state: Optional[int] = Field(None, ge=0, le=9, description="Sea state (0-9)")
    
    # Acoustic-specific metadata
    beam_pattern: Optional[str] = Field(None, description="Beam pattern type")
    array_geometry: Optional[str] = Field(None, description="Array geometry")
    processing_method: Optional[str] = Field(None, description="Processing method")


class RadarDetection(BaseDetection):
    """Radar-based detection (Dspnor, etc.)"""
    
    source: Literal["dspnor", "radar"] = Field(description="Radar source type")
    range_m: float = Field(ge=0, description="Range in meters")
    elevation_deg: Optional[float] = Field(None, ge=-90, le=90, description="Elevation in degrees")
    doppler_hz: Optional[float] = Field(None, description="Doppler frequency in Hz")
    rcs_dbsm: Optional[float] = Field(None, description="Radar cross-section in dBsm")
    
    # Radar-specific metadata
    scan_mode: Optional[str] = Field(None, description="Scan mode")
    pulse_width_us: Optional[float] = Field(None, ge=0, description="Pulse width in microseconds")
    prf_hz: Optional[float] = Field(None, ge=0, description="Pulse repetition frequency in Hz")


class FusedDetection(BaseDetection):
    """Fused detection from multiple sources"""
    
    source: Literal["fused", "fusion"] = Field(description="Fusion source type")
    contributing_sources: List[str] = Field(description="List of contributing source types")
    fusion_method: str = Field(description="Fusion method used")
    fusion_confidence: float = Field(ge=0, le=1, description="Fusion confidence")
    
    # Fusion-specific metadata
    source_weights: Dict[str, float] = Field(
        default_factory=dict, description="Weights for each source"
    )
    source_confidences: Dict[str, float] = Field(
        default_factory=dict, description="Confidence from each source"
    )


# Union type for all detection types
Detection = Union[RFDetection, VisionDetection, AcousticDetection, RadarDetection, FusedDetection]


class DetectionEvent(BaseModel):
    """Standard detection event published to event manager"""
    
    event_type: str = Field(description="Event type identifier")
    detection: Detection = Field(description="Detection data")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    plugin_name: str = Field(description="Plugin that generated the event")
    
    # Event metadata
    store_in_db: bool = Field(default=True, description="Whether to store in database")
    priority: int = Field(default=0, description="Event priority (higher = more important)")
    tags: List[str] = Field(default_factory=list, description="Event tags")


class BearingUpdate(BaseModel):
    """Bearing update for existing track"""
    
    track_id: str = Field(description="Track identifier")
    bearing_deg: float = Field(ge=0, lt=360, description="New bearing in degrees")
    confidence: float = Field(ge=0, le=1, description="Bearing confidence")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = Field(description="Source of bearing update")
    
    # Optional fields
    range_m: Optional[float] = Field(None, ge=0, description="Range in meters")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ConfidenceUpdate(BaseModel):
    """Confidence update for existing track"""
    
    track_id: str = Field(description="Track identifier")
    confidence_0_1: float = Field(ge=0, le=1, description="New confidence [0, 1]")
    reason: str = Field(description="Reason for confidence change")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = Field(description="Source of confidence update")
    
    # Optional fields
    details: Dict[str, Any] = Field(default_factory=dict, description="Update details")
    contributing_cues: Dict[str, float] = Field(
        default_factory=dict, description="Contributing cue scores"
    )


class RangeUpdate(BaseModel):
    """Range update for existing track"""
    
    track_id: str = Field(description="Track identifier")
    range_km: float = Field(ge=0, description="Range in kilometers")
    sigma_km: float = Field(ge=0, description="Range uncertainty in kilometers")
    mode: str = Field(description="Range estimation mode")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = Field(description="Source of range update")
    
    # Optional fields
    details: Dict[str, Any] = Field(default_factory=dict, description="Range estimation details")
    contributing_cues: Dict[str, Dict[str, float]] = Field(
        default_factory=dict, description="Contributing cue data"
    )


class TrackState(BaseModel):
    """Complete track state"""
    
    track_id: str = Field(description="Unique track identifier")
    first_seen: datetime = Field(description="First detection timestamp")
    last_seen: datetime = Field(description="Last detection timestamp")
    current_bearing_deg: float = Field(ge=0, lt=360, description="Current bearing in degrees")
    current_range_km: Optional[float] = Field(None, ge=0, description="Current range in kilometers")
    current_confidence: float = Field(ge=0, le=1, description="Current confidence")
    
    # Track metadata
    source_types: List[str] = Field(description="Types of sources that have contributed")
    detection_count: int = Field(ge=0, description="Total number of detections")
    last_update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Optional fields
    altitude_m: Optional[float] = Field(None, description="Current altitude in meters")
    speed_ms: Optional[float] = Field(None, ge=0, description="Current speed in m/s")
    course_deg: Optional[float] = Field(None, ge=0, lt=360, description="Current course in degrees")
    
    # Track metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional track metadata")


# Utility functions for creating detections
def create_rf_detection(
    bearing_deg: float,
    confidence: float,
    track_id: str,
    source: str = "rf",
    **kwargs
) -> RFDetection:
    """Create an RF detection with proper normalization"""
    return RFDetection(
        timestamp=datetime.now(timezone.utc),
        source=source,
        bearing_deg=bearing_deg,
        confidence=confidence,
        track_id=track_id,
        **kwargs
    )


def create_vision_detection(
    bearing_deg: float,
    confidence: float,
    track_id: str,
    verified: bool,
    label: str,
    source: str = "vision",
    **kwargs
) -> VisionDetection:
    """Create a vision detection with proper normalization"""
    return VisionDetection(
        timestamp=datetime.now(timezone.utc),
        source=source,
        bearing_deg=bearing_deg,
        confidence=confidence,
        track_id=track_id,
        verified=verified,
        label=label,
        **kwargs
    )


def create_acoustic_detection(
    bearing_deg: float,
    confidence: float,
    track_id: str,
    source: str = "acoustic",
    **kwargs
) -> AcousticDetection:
    """Create an acoustic detection with proper normalization"""
    return AcousticDetection(
        timestamp=datetime.now(timezone.utc),
        source=source,
        bearing_deg=bearing_deg,
        confidence=confidence,
        track_id=track_id,
        **kwargs
    )


def create_radar_detection(
    bearing_deg: float,
    confidence: float,
    track_id: str,
    range_m: float,
    source: str = "radar",
    **kwargs
) -> RadarDetection:
    """Create a radar detection with proper normalization"""
    return RadarDetection(
        timestamp=datetime.now(timezone.utc),
        source=source,
        bearing_deg=bearing_deg,
        confidence=confidence,
        track_id=track_id,
        range_m=range_m,
        **kwargs
    )


def create_fused_detection(
    bearing_deg: float,
    confidence: float,
    track_id: str,
    contributing_sources: List[str],
    fusion_method: str = "weighted_average",
    **kwargs
) -> FusedDetection:
    """Create a fused detection with proper normalization"""
    return FusedDetection(
        timestamp=datetime.now(timezone.utc),
        source="fused",
        bearing_deg=bearing_deg,
        confidence=confidence,
        track_id=track_id,
        contributing_sources=contributing_sources,
        fusion_method=fusion_method,
        fusion_confidence=confidence,
        **kwargs
    )


def normalize_detection_bearing(detection: Detection, bow_offset_deg: float = 0.0) -> Detection:
    """Normalize detection bearing to bow-relative coordinates"""
    # Apply bow offset
    normalized_bearing = (detection.bearing_deg + bow_offset_deg) % 360.0
    
    # Create new detection with normalized bearing
    detection_dict = detection.model_dump()
    detection_dict["bearing_deg"] = normalized_bearing
    
    # Recreate detection with proper type
    if isinstance(detection, RFDetection):
        return RFDetection(**detection_dict)
    elif isinstance(detection, VisionDetection):
        return VisionDetection(**detection_dict)
    elif isinstance(detection, AcousticDetection):
        return AcousticDetection(**detection_dict)
    elif isinstance(detection, RadarDetection):
        return RadarDetection(**detection_dict)
    elif isinstance(detection, FusedDetection):
        return FusedDetection(**detection_dict)
    else:
        return BaseDetection(**detection_dict)
