"""
Data schemas for Dspnor plugin
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


@dataclass
class D2DHeader:
    """D2D protocol header"""

    protocol: str
    version: str
    type: str
    length: int


@dataclass
class DiscoveryBeacon:
    """Multicast discovery beacon"""

    ip_address: str
    port: int
    unit_name: str
    serial_number: str
    firmware_version: str
    capabilities: list[str]


@dataclass
class CAT010Track:
    """Raw CAT-010 track data"""

    time_of_day: float | None = None  # I010/140
    track_number: int | None = None  # I010/161
    target_address: int | None = None  # I010/041
    track_quality: int | None = None  # I010/042
    ground_speed: float | None = None  # I010/200
    track_angle_rate: float | None = None  # I010/202
    mode_3a_code: int | None = None  # I010/220
    target_id: str | None = None  # I010/245
    has_mmsi: bool = False  # I010/245 bit-54
    position_polar: tuple | None = None  # (range, bearing) in meters/degrees
    position_cartesian: tuple | None = None  # (x, y) in meters
    velocity_polar: tuple | None = None  # (speed, heading) in m/s/degrees
    velocity_cartesian: tuple | None = None  # (vx, vy) in m/s


@dataclass
class StatusData:
    """Runtime status data"""

    timestamp: datetime
    internal_sources: dict[str, Any]
    external_sources: dict[str, Any]
    temperatures: dict[str, float]
    mode: str
    sensors: dict[str, Any]
    health_status: str


@dataclass
class NMEAData:
    """NMEA heading/GPS data"""

    timestamp: datetime
    heading_deg_true: float | None = None
    course_over_ground: float | None = None
    speed_over_ground: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = None
    is_stale: bool = False


class NormalizedDetection(BaseModel):
    """Normalized detection for TheBox event system"""

    object_id: str = Field(..., description="Unique object identifier")
    time_utc: datetime = Field(..., description="Detection timestamp UTC")
    bearing_deg_true: float = Field(..., description="Bearing in degrees true")
    bearing_error_deg: float = Field(
        default=5.0, description="Bearing error in degrees"
    )
    distance_m: float | None = Field(default=None, description="Distance in meters")
    distance_error_m: float | None = Field(
        default=None, description="Distance error in meters"
    )
    altitude_m: float | None = Field(default=0.0, description="Altitude in meters")
    altitude_error_m: float | None = Field(
        default=20.0, description="Altitude error in meters"
    )
    speed_mps: float | None = Field(default=None, description="Speed in m/s")
    course_deg: float | None = Field(default=None, description="Course in degrees")
    confidence: int = Field(default=75, ge=0, le=100, description="Confidence 0-100")
    track_id: str | None = Field(default=None, description="Original track ID")
    has_mmsi: bool = Field(default=False, description="Has MMSI identification")
    raw_data: dict[str, Any] = Field(
        default_factory=dict, description="Raw detection data"
    )


class D2DCommand(BaseModel):
    """D2D command structure"""

    command: str = Field(..., description="Command name")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Command parameters"
    )
    timestamp: datetime | None = Field(default=None, description="Command timestamp")


class ServiceConfig(BaseModel):
    """Service configuration"""

    enabled: bool = Field(default=False, description="Service enabled")
    ip: str = Field(default="", description="Service IP address")
    port: int = Field(default=0, description="Service port")
    protocol: str = Field(default="UDP", description="Service protocol")


class UnitInfo(BaseModel):
    """Unit information from discovery"""

    ip_address: str = Field(..., description="Unit IP address")
    port: int = Field(..., description="Unit port")
    unit_name: str = Field(..., description="Unit name")
    serial_number: str = Field(..., description="Unit serial number")
    firmware_version: str = Field(..., description="Firmware version")
    capabilities: list[str] = Field(
        default_factory=list, description="Unit capabilities"
    )
    last_seen: datetime = Field(
        default_factory=datetime.now, description="Last discovery time"
    )
