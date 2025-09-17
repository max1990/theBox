"""
Metrics collection for Dspnor plugin
"""

from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class DspnorMetrics:
    """Metrics collector for Dspnor plugin"""

    def __init__(self):
        self.logger = logger.bind(component="metrics")

        # Message counters
        self.messages_ok = 0
        self.messages_bad = 0
        self.detections_out = 0
        self.reconnects = 0
        self.overrate_drops = 0

        # Data counters
        self.cat010_bytes_in = 0
        self.nmea_msgs = 0

        # Status tracking
        self.last_status_time: datetime | None = None
        self.last_discovery_time: datetime | None = None
        self.last_cat010_time: datetime | None = None
        self.last_nmea_time: datetime | None = None

        # Connection status
        self.discovery_connected = False
        self.info_connected = False
        self.cat010_connected = False
        self.nmea_connected = False

        # Error tracking
        self.last_error: str | None = None
        self.error_count = 0

        # Performance tracking
        self.avg_parse_time_ms = 0.0
        self.parse_times: list = []
        self.max_parse_times = 100  # Keep last 100 parse times

    def increment_messages_ok(self):
        """Increment successful message counter"""
        self.messages_ok += 1

    def increment_messages_bad(self):
        """Increment bad message counter"""
        self.messages_bad += 1

    def increment_detections_out(self):
        """Increment output detections counter"""
        self.detections_out += 1

    def increment_reconnects(self):
        """Increment reconnection counter"""
        self.reconnects += 1

    def increment_overrate_drops(self):
        """Increment overrate drop counter"""
        self.overrate_drops += 1

    def add_cat010_bytes(self, bytes_count: int):
        """Add CAT-010 bytes received"""
        self.cat010_bytes_in += bytes_count
        self.last_cat010_time = datetime.now()

    def increment_nmea_msgs(self):
        """Increment NMEA message counter"""
        self.nmea_msgs += 1
        self.last_nmea_time = datetime.now()

    def update_status_time(self):
        """Update last status time"""
        self.last_status_time = datetime.now()

    def update_discovery_time(self):
        """Update last discovery time"""
        self.last_discovery_time = datetime.now()

    def set_connection_status(
        self,
        discovery: bool = None,
        info: bool = None,
        cat010: bool = None,
        nmea: bool = None,
    ):
        """Update connection status"""
        if discovery is not None:
            self.discovery_connected = discovery
        if info is not None:
            self.info_connected = info
        if cat010 is not None:
            self.cat010_connected = cat010
        if nmea is not None:
            self.nmea_connected = nmea

    def record_error(self, error: str):
        """Record error"""
        self.last_error = error
        self.error_count += 1
        self.logger.error("Metrics error recorded", error=error)

    def record_parse_time(self, parse_time_ms: float):
        """Record parse time for performance tracking"""
        self.parse_times.append(parse_time_ms)
        if len(self.parse_times) > self.max_parse_times:
            self.parse_times.pop(0)

        # Update average
        self.avg_parse_time_ms = sum(self.parse_times) / len(self.parse_times)

    def get_last_status_age_seconds(self) -> float | None:
        """Get age of last status update in seconds"""
        if not self.last_status_time:
            return None
        return (datetime.now() - self.last_status_time).total_seconds()

    def get_last_discovery_age_seconds(self) -> float | None:
        """Get age of last discovery update in seconds"""
        if not self.last_discovery_time:
            return None
        return (datetime.now() - self.last_discovery_time).total_seconds()

    def get_last_cat010_age_seconds(self) -> float | None:
        """Get age of last CAT-010 update in seconds"""
        if not self.last_cat010_time:
            return None
        return (datetime.now() - self.last_cat010_time).total_seconds()

    def get_last_nmea_age_seconds(self) -> float | None:
        """Get age of last NMEA update in seconds"""
        if not self.last_nmea_time:
            return None
        return (datetime.now() - self.last_nmea_time).total_seconds()

    def is_status_stale(self, max_age_seconds: int = 10) -> bool:
        """Check if status is stale"""
        age = self.get_last_status_age_seconds()
        return age is None or age > max_age_seconds

    def is_discovery_stale(self, max_age_seconds: int = 30) -> bool:
        """Check if discovery is stale"""
        age = self.get_last_discovery_age_seconds()
        return age is None or age > max_age_seconds

    def is_cat010_stale(self, max_age_seconds: int = 60) -> bool:
        """Check if CAT-010 data is stale"""
        age = self.get_last_cat010_age_seconds()
        return age is None or age > max_age_seconds

    def is_nmea_stale(self, max_age_seconds: int = 10) -> bool:
        """Check if NMEA data is stale"""
        age = self.get_last_nmea_age_seconds()
        return age is None or age > max_age_seconds

    def get_summary(self) -> dict[str, Any]:
        """Get metrics summary"""
        return {
            "messages_ok": self.messages_ok,
            "messages_bad": self.messages_bad,
            "detections_out": self.detections_out,
            "reconnects": self.reconnects,
            "overrate_drops": self.overrate_drops,
            "cat010_bytes_in": self.cat010_bytes_in,
            "nmea_msgs": self.nmea_msgs,
            "last_status_age_s": self.get_last_status_age_seconds(),
            "last_discovery_age_s": self.get_last_discovery_age_seconds(),
            "last_cat010_age_s": self.get_last_cat010_age_seconds(),
            "last_nmea_age_s": self.get_last_nmea_age_seconds(),
            "connections": {
                "discovery": self.discovery_connected,
                "info": self.info_connected,
                "cat010": self.cat010_connected,
                "nmea": self.nmea_connected,
            },
            "errors": {"last_error": self.last_error, "error_count": self.error_count},
            "performance": {
                "avg_parse_time_ms": round(self.avg_parse_time_ms, 2),
                "parse_samples": len(self.parse_times),
            },
        }

    def reset(self):
        """Reset all metrics"""
        self.messages_ok = 0
        self.messages_bad = 0
        self.detections_out = 0
        self.reconnects = 0
        self.overrate_drops = 0
        self.cat010_bytes_in = 0
        self.nmea_msgs = 0
        self.error_count = 0
        self.last_error = None
        self.parse_times.clear()
        self.avg_parse_time_ms = 0.0

        self.logger.info("Metrics reset")

    def get_health_status(self) -> str:
        """Get overall health status"""
        # Check for critical errors
        if self.error_count > 100:  # Too many errors
            return "error"

        # Check for stale data
        if self.is_status_stale(30):  # Status older than 30s
            return "warning"

        if self.is_cat010_stale(120):  # No CAT-010 for 2 minutes
            return "warning"

        if self.is_nmea_stale(30):  # No NMEA for 30s
            return "warning"

        # Check connection status
        if not self.discovery_connected:
            return "error"

        if not self.info_connected:
            return "warning"

        if not self.cat010_connected:
            return "warning"

        # All good
        return "good"
