"""
Data schemas for Dspnor plugin
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime
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
    capabilities: List[str]


@dataclass
class CAT010Track:
    """Raw CAT-010 track data"""
    time_of_day: Optional[float] = None  # I010/140
    track_number: Optional[int] = None   # I010/161
    target_address: Optional[int] = None # I010/041
    track_quality: Optional[int] = None  # I010/042
    ground_speed: Optional[float] = None # I010/200
    track_angle_rate: Optional[float] = None # I010/202
    mode_3a_code: Optional[int] = None   # I010/220
    target_id: Optional[str] = None      # I010/245
    has_mmsi: bool = False               # I010/245 bit-54
    position_polar: Optional[tuple] = None  # (range, bearing) in meters/degrees
    position_cartesian: Optional[tuple] = None  # (x, y) in meters
    velocity_polar: Optional[tuple] = None  # (speed, heading) in m/s/degrees
    velocity_cartesian: Optional[tuple] = None  # (vx, vy) in m/s


@dataclass
class StatusData:
    """Runtime status data"""
    timestamp: datetime
    internal_sources: Dict[str, Any]
    external_sources: Dict[str, Any]
    temperatures: Dict[str, float]
    mode: str
    sensors: Dict[str, Any]
    health_status: str


@dataclass
class NMEAData:
    """NMEA heading/GPS data"""
    timestamp: datetime
    heading_deg_true: Optional[float] = None
    course_over_ground: Optional[float] = None
    speed_over_ground: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    is_stale: bool = False


class NormalizedDetection(BaseModel):
    """Normalized detection for TheBox event system"""
    object_id: str = Field(..., description="Unique object identifier")
    time_utc: datetime = Field(..., description="Detection timestamp UTC")
    bearing_deg_true: float = Field(..., description="Bearing in degrees true")
    bearing_error_deg: float = Field(default=5.0, description="Bearing error in degrees")
    distance_m: Optional[float] = Field(default=None, description="Distance in meters")
    distance_error_m: Optional[float] = Field(default=None, description="Distance error in meters")
    altitude_m: Optional[float] = Field(default=0.0, description="Altitude in meters")
    altitude_error_m: Optional[float] = Field(default=20.0, description="Altitude error in meters")
    speed_mps: Optional[float] = Field(default=None, description="Speed in m/s")
    course_deg: Optional[float] = Field(default=None, description="Course in degrees")
    confidence: int = Field(default=75, ge=0, le=100, description="Confidence 0-100")
    track_id: Optional[str] = Field(default=None, description="Original track ID")
    has_mmsi: bool = Field(default=False, description="Has MMSI identification")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Raw detection data")


class D2DCommand(BaseModel):
    """D2D command structure"""
    command: str = Field(..., description="Command name")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Command parameters")
    timestamp: Optional[datetime] = Field(default=None, description="Command timestamp")


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
    capabilities: List[str] = Field(default_factory=list, description="Unit capabilities")
    last_seen: datetime = Field(default_factory=datetime.now, description="Last discovery time")
