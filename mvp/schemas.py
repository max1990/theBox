from typing import Optional, Literal, Dict
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


class VisionResult(BaseModel):
    track_id: str | int
    verified: bool
    label: str | None = None
    latency_ms: int


class ConfidenceUpdate(BaseModel):
    track_id: str | int
    previous: float
    updated: float
    reason: str


