"""
Pydantic models for MARA plugin normalized detection schema.
"""
from datetime import datetime
from typing import Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
import math


class NormalizedDetection(BaseModel):
    """Normalized detection event schema matching TheBox conventions."""
    
    source: Literal["mara"] = "mara"
    sensor_channel: Literal["EO", "IR", "ACOUSTIC", "UNKNOWN"] = "UNKNOWN"
    event_type: Optional[Literal["DETECTION", "TRACK", "HEARTBEAT", "STATUS"]] = None
    label: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    bearing_deg: Optional[float] = Field(None, ge=0.0, lt=360.0)
    elev_deg: Optional[float] = Field(None, ge=-90.0, le=90.0)
    range_km: Optional[float] = Field(None, ge=0.0, le=1000.0)  # Max 1000km
    lat: Optional[float] = Field(None, ge=-90.0, le=90.0)
    lon: Optional[float] = Field(None, ge=-180.0, le=180.0)
    speed_mps: Optional[float] = Field(None, ge=0.0, le=1000.0)  # Max 1000 m/s
    heading_deg: Optional[float] = Field(None, ge=0.0, lt=360.0)
    track_id: Optional[Union[str, int]] = None
    timestamp_utc: datetime
    raw: Union[dict, str] = Field(..., description="Original MARA record for traceability")

    @field_validator('bearing_deg', 'heading_deg', mode='before')
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

    @field_validator('elev_deg', mode='before')
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

    @field_validator('confidence', mode='before')
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

    @field_validator('range_km', mode='before')
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

    @field_validator('speed_mps', mode='before')
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

    @field_validator('lat', mode='before')
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

    @field_validator('lon', mode='before')
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

    @field_validator('sensor_channel', mode='before')
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

    @model_validator(mode='after')
    def determine_event_type(self):
        """Determine event type based on content."""
        if self.event_type and self.event_type.upper() in ["DETECTION", "TRACK", "HEARTBEAT", "STATUS"]:
            return self
        
        # Check for heartbeat indicators in raw data
        raw_str = str(self.raw).lower()
        if 'heartbeat' in raw_str or 'status' in raw_str:
            self.event_type = "HEARTBEAT"
        elif 'track_id' in raw_str or 'track' in raw_str:
            self.event_type = "TRACK"
        else:
            self.event_type = "DETECTION"
        
        return self

    model_config = {
        "validate_assignment": True,
        "use_enum_values": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat() + 'Z' if v.tzinfo is None else v.isoformat()
        }
    }


class MARARawData(BaseModel):
    """Internal model for parsing raw MARA data."""
    
    timestamp: Optional[str] = None
    sensor_id: Optional[str] = None
    object_id: Optional[str] = None
    track_id: Optional[Union[str, int]] = None
    confidence: Optional[Union[float, str]] = None
    bearing_deg: Optional[Union[float, str]] = None
    elevation_deg: Optional[Union[float, str]] = None
    range_m: Optional[Union[float, str]] = None
    lat: Optional[Union[float, str]] = None
    lon: Optional[Union[float, str]] = None
    speed_mps: Optional[Union[float, str]] = None
    heading_deg: Optional[Union[float, str]] = None
    label: Optional[str] = None
    channel: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    event_type: Optional[str] = None

    model_config = {
        "extra": "allow"  # Allow additional fields from MARA data
    }
