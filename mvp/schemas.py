from typing import Optional, Literal, Dict, Tuple, Union
from pydantic import BaseModel, Field


class NormalizedDetection(BaseModel):
    timestamp_ms: int
    source: str = Field(default="droneshield")
    bearing_deg: float
    lat: Optional[float] = None
    lon: Optional[float] = None
    sensor_track_key: str
    signal: Optional[Dict] = None


class CameraCommand(BaseModel):
    action: Literal["slew"]
    bearing_deg: float
    track_id: str | int


class SearchResult(BaseModel):
    track_id: str | int
    verified: bool


class CLSMessage(BaseModel):
    object_id: str
    type: str = "UNDERWATER"
    brand_model: str = "Brand Model"
    affiliation: str = "UNKNOWN"
    details_url: str


class SGTMessage(BaseModel):
    object_id: str
    yyyymmdd: str
    hhmmss: str
    distance_m: float
    distance_err_m: float
    bearing_deg: float
    bearing_err_deg: float
    altitude_m: float
    altitude_err_m: float


class RangeEstimate(BaseModel):
    """Range estimation result with uncertainty and method details"""
    range_km: Optional[float] = None
    sigma_km: Optional[float] = None
    mode: str = "unknown"
    details: Dict = Field(default_factory=dict)


class VisionResult(BaseModel):
    """Vision verification result with tracking and latency info"""
    verified: bool
    label: str
    latency_ms: int
    bbox: Optional[Tuple[float, float, float, float]] = None  # (x1, y1, x2, y2)
    tracker: Optional[Dict] = None


class ConfidenceUpdate(BaseModel):
    """Confidence update with reasoning and details"""
    confidence_0_1: float
    reason: str
    details: Dict = Field(default_factory=dict)


