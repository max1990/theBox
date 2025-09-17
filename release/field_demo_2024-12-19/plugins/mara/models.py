"""
Pydantic models for MARA plugin normalized detection schema.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class NormalizedDetection(BaseModel):
    """Normalized detection event schema matching TheBox conventions."""

    source: Literal["mara"] = "mara"
    sensor_channel: Literal["EO", "IR", "ACOUSTIC", "UNKNOWN"] = "UNKNOWN"
    event_type: Literal["DETECTION", "TRACK", "HEARTBEAT", "STATUS"] | None = None
    label: str | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    bearing_deg: float | None = Field(None, ge=0.0, lt=360.0)
    elev_deg: float | None = Field(None, ge=-90.0, le=90.0)
    range_km: float | None = Field(None, ge=0.0, le=1000.0)  # Max 1000km
    lat: float | None = Field(None, ge=-90.0, le=90.0)
    lon: float | None = Field(None, ge=-180.0, le=180.0)
    speed_mps: float | None = Field(None, ge=0.0, le=1000.0)  # Max 1000 m/s
    heading_deg: float | None = Field(None, ge=0.0, lt=360.0)
    track_id: str | int | None = None
    timestamp_utc: datetime
    raw: dict | str = Field(
        ..., description="Original MARA record for traceability"
    )

    @field_validator("bearing_deg", "heading_deg", mode="before")
    @classmethod
    def normalize_angle(cls, v):
        """Normalize angles to 0-360 range."""
        if v is None:
            return v
        try:
            v = float(v)
            # Normalize to 0-360 range
            while v < 0:
                v += 360
            while v >= 360:
                v -= 360
            return v
        except (ValueError, TypeError):
            return None

    @field_validator("elev_deg", mode="before")
    @classmethod
    def clamp_elevation(cls, v):
        """Clamp elevation to -90 to +90 degrees."""
        if v is None:
            return v
        try:
            v = float(v)
            return max(-90.0, min(90.0, v))
        except (ValueError, TypeError):
            return None

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v):
        """Clamp confidence to 0.0-1.0 range."""
        if v is None:
            return v
        try:
            v = float(v)
            return max(0.0, min(1.0, v))
        except (ValueError, TypeError):
            return None

    @field_validator("range_km", mode="before")
    @classmethod
    def convert_range_to_km(cls, v):
        """Convert range from meters to kilometers if needed."""
        if v is None:
            return v
        try:
            v = float(v)
            # If range is > 1000, assume it's in meters and convert to km
            if v > 1000:
                return v / 1000.0
            return v
        except (ValueError, TypeError):
            return None

    @field_validator("speed_mps", mode="before")
    @classmethod
    def clamp_speed(cls, v):
        """Clamp speed to reasonable range."""
        if v is None:
            return v
        try:
            v = float(v)
            return max(0.0, min(1000.0, v))
        except (ValueError, TypeError):
            return None

    @field_validator("lat", mode="before")
    @classmethod
    def clamp_latitude(cls, v):
        """Clamp latitude to valid range."""
        if v is None:
            return v
        try:
            v = float(v)
            return max(-90.0, min(90.0, v))
        except (ValueError, TypeError):
            return None

    @field_validator("lon", mode="before")
    @classmethod
    def clamp_longitude(cls, v):
        """Clamp longitude to valid range."""
        if v is None:
            return v
        try:
            v = float(v)
            return max(-180.0, min(180.0, v))
        except (ValueError, TypeError):
            return None

    @field_validator("sensor_channel", mode="before")
    @classmethod
    def normalize_channel(cls, v):
        """Normalize sensor channel to standard values."""
        if v is None:
            return "UNKNOWN"
        v = str(v).upper().strip()
        if v in ["EO", "ELECTRO-OPTICAL", "VISUAL", "CAMERA"]:
            return "EO"
        elif v in ["IR", "INFRARED", "THERMAL"]:
            return "IR"
        elif v in ["ACOUSTIC", "AUDIO", "SOUND", "MICROPHONE"]:
            return "ACOUSTIC"
        else:
            return "UNKNOWN"

    @model_validator(mode="after")
    def determine_event_type(self):
        """Determine event type based on content."""
        if self.event_type and self.event_type.upper() in [
            "DETECTION",
            "TRACK",
            "HEARTBEAT",
            "STATUS",
        ]:
            return self

        # Check for heartbeat indicators in raw data
        raw_str = str(self.raw).lower()
        if "heartbeat" in raw_str or "status" in raw_str:
            self.event_type = "HEARTBEAT"
        elif "track_id" in raw_str or "track" in raw_str:
            self.event_type = "TRACK"
        else:
            self.event_type = "DETECTION"

        return self

    model_config = {
        "validate_assignment": True,
        "use_enum_values": True,
        "json_encoders": {
            datetime: lambda v: (
                v.isoformat() + "Z" if v.tzinfo is None else v.isoformat()
            )
        },
    }


class MARARawData(BaseModel):
    """Internal model for parsing raw MARA data."""

    timestamp: str | None = None
    sensor_id: str | None = None
    object_id: str | None = None
    track_id: str | int | None = None
    confidence: float | str | None = None
    bearing_deg: float | str | None = None
    elevation_deg: float | str | None = None
    range_m: float | str | None = None
    lat: float | str | None = None
    lon: float | str | None = None
    speed_mps: float | str | None = None
    heading_deg: float | str | None = None
    label: str | None = None
    channel: str | None = None
    status: str | None = None
    message: str | None = None
    event_type: str | None = None

    model_config = {"extra": "allow"}  # Allow additional fields from MARA data
