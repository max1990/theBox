"""
NMEA ingestion for Dspnor plugin
"""

import socket
import threading
from collections.abc import Callable
from datetime import datetime

import structlog

from .constants import DEFAULT_NMEA_UDP_PORT, NMEA_GGA, NMEA_HDG, NMEA_RMC, NMEA_VTG
from .schemas import NMEAData

logger = structlog.get_logger(__name__)


class NMEAParser:
    """NMEA sentence parser"""

    def __init__(self):
        self.logger = logger.bind(component="nmea_parser")
        self.sentence_patterns = {
            NMEA_RMC: self._parse_rmc,
            NMEA_VTG: self._parse_vtg,
            NMEA_GGA: self._parse_gga,
            NMEA_HDG: self._parse_hdg,
        }

    def parse_sentence(self, sentence: str) -> NMEAData | None:
        """Parse NMEA sentence"""
        try:
            # Validate checksum
            if not self._validate_checksum(sentence):
                self.logger.warning("Invalid NMEA checksum", sentence=sentence[:50])
                return None

            # Extract sentence type
            parts = sentence.split(",")
            if len(parts) < 2:
                return None

            sentence_type = parts[0][3:]  # Remove $XX prefix

            # Parse based on sentence type
            if sentence_type in self.sentence_patterns:
                return self.sentence_patterns[sentence_type](parts)
            else:
                self.logger.debug("Unsupported NMEA sentence type", type=sentence_type)
                return None

        except Exception as e:
            self.logger.error(
                "Failed to parse NMEA sentence", sentence=sentence[:50], error=str(e)
            )
            return None

    def _validate_checksum(self, sentence: str) -> bool:
        """Validate NMEA checksum"""
        if "*" not in sentence:
            return True  # No checksum to validate

        try:
            parts = sentence.split("*")
            if len(parts) != 2:
                return False

            data = parts[0][1:]  # Remove $ prefix
            checksum = parts[1]

            # Calculate checksum
            calculated = 0
            for char in data:
                calculated ^= ord(char)

            return f"{calculated:02X}" == checksum.upper()

        except:
            return False

    def _parse_rmc(self, parts: list) -> NMEAData | None:
        """Parse RMC sentence"""
        try:
            if len(parts) < 12:
                return None

            # Extract time
            time_str = parts[1] if parts[1] else None
            date_str = parts[9] if parts[9] else None

            timestamp = self._parse_timestamp(time_str, date_str)

            # Extract position
            lat_str = parts[3] if parts[3] else None
            lat_dir = parts[4] if parts[4] else None
            lon_str = parts[5] if parts[5] else None
            lon_dir = parts[6] if parts[6] else None

            latitude = self._parse_latitude(lat_str, lat_dir)
            longitude = self._parse_longitude(lon_str, lon_dir)

            # Extract course and speed
            course = self._parse_float(parts[8])  # Track made good
            speed = self._parse_float(parts[7])  # Speed over ground

            return NMEAData(
                timestamp=timestamp,
                heading_deg_true=course,
                course_over_ground=course,
                speed_over_ground=speed,
                latitude=latitude,
                longitude=longitude,
            )

        except Exception as e:
            self.logger.error("Failed to parse RMC", error=str(e))
            return None

    def _parse_vtg(self, parts: list) -> NMEAData | None:
        """Parse VTG sentence"""
        try:
            if len(parts) < 10:
                return None

            # Extract course and speed
            course_true = self._parse_float(parts[1])  # Track made good (true)
            course_mag = self._parse_float(parts[3])  # Track made good (magnetic)
            speed_kts = self._parse_float(parts[5])  # Speed in knots
            speed_kmh = self._parse_float(parts[7])  # Speed in km/h

            # Convert speed to m/s
            speed_mps = None
            if speed_kts is not None:
                speed_mps = speed_kts * 0.514444  # knots to m/s
            elif speed_kmh is not None:
                speed_mps = speed_kmh / 3.6  # km/h to m/s

            return NMEAData(
                timestamp=datetime.now(),
                heading_deg_true=course_true,
                course_over_ground=course_true,
                speed_over_ground=speed_mps,
            )

        except Exception as e:
            self.logger.error("Failed to parse VTG", error=str(e))
            return None

    def _parse_gga(self, parts: list) -> NMEAData | None:
        """Parse GGA sentence"""
        try:
            if len(parts) < 15:
                return None

            # Extract time
            time_str = parts[1] if parts[1] else None
            timestamp = self._parse_timestamp(time_str)

            # Extract position
            lat_str = parts[2] if parts[2] else None
            lat_dir = parts[3] if parts[3] else None
            lon_str = parts[4] if parts[4] else None
            lon_dir = parts[5] if parts[5] else None

            latitude = self._parse_latitude(lat_str, lat_dir)
            longitude = self._parse_longitude(lon_str, lon_dir)

            # Extract altitude
            altitude = self._parse_float(parts[9])  # Altitude in meters

            return NMEAData(
                timestamp=timestamp,
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
            )

        except Exception as e:
            self.logger.error("Failed to parse GGA", error=str(e))
            return None

    def _parse_hdg(self, parts: list) -> NMEAData | None:
        """Parse HDG sentence"""
        try:
            if len(parts) < 4:
                return None

            # Extract heading
            heading = self._parse_float(parts[1])  # Magnetic heading
            deviation = self._parse_float(parts[2])  # Deviation
            variation = self._parse_float(parts[3])  # Variation

            # Convert to true heading
            heading_true = heading
            if deviation is not None:
                heading_true += deviation
            if variation is not None:
                heading_true += variation

            return NMEAData(timestamp=datetime.now(), heading_deg_true=heading_true)

        except Exception as e:
            self.logger.error("Failed to parse HDG", error=str(e))
            return None

    def _parse_timestamp(
        self, time_str: str | None, date_str: str | None = None
    ) -> datetime:
        """Parse NMEA timestamp"""
        if not time_str:
            return datetime.now()

        try:
            # Parse time (HHMMSS.SSS)
            if "." in time_str:
                time_part, ms_part = time_str.split(".", 1)
                ms = int(ms_part[:3].ljust(3, "0"))  # Pad to 3 digits
            else:
                time_part = time_str
                ms = 0

            hour = int(time_part[:2])
            minute = int(time_part[2:4])
            second = int(time_part[4:6])

            # Parse date if provided (DDMMYY)
            if date_str and len(date_str) == 6:
                day = int(date_str[:2])
                month = int(date_str[2:4])
                year = 2000 + int(date_str[4:6])
            else:
                now = datetime.now()
                day = now.day
                month = now.month
                year = now.year

            return datetime(year, month, day, hour, minute, second, ms * 1000)

        except:
            return datetime.now()

    def _parse_latitude(
        self, lat_str: str | None, lat_dir: str | None
    ) -> float | None:
        """Parse latitude from NMEA format"""
        if not lat_str or not lat_dir:
            return None

        try:
            # Format: DDMM.MMMM
            if "." in lat_str:
                dd_part = lat_str.split(".")[0]
                mm_part = lat_str.split(".")[1]
            else:
                dd_part = lat_str[:-2]
                mm_part = lat_str[-2:]

            degrees = float(dd_part)
            minutes = float(f"0.{mm_part}")

            latitude = degrees + (minutes / 60.0)

            if lat_dir.upper() == "S":
                latitude = -latitude

            return latitude

        except:
            return None

    def _parse_longitude(
        self, lon_str: str | None, lon_dir: str | None
    ) -> float | None:
        """Parse longitude from NMEA format"""
        if not lon_str or not lon_dir:
            return None

        try:
            # Format: DDDMM.MMMM
            if "." in lon_str:
                ddd_part = lon_str.split(".")[0]
                mm_part = lon_str.split(".")[1]
            else:
                ddd_part = lon_str[:-2]
                mm_part = lon_str[-2:]

            degrees = float(ddd_part)
            minutes = float(f"0.{mm_part}")

            longitude = degrees + (minutes / 60.0)

            if lon_dir.upper() == "W":
                longitude = -longitude

            return longitude

        except:
            return None

    def _parse_float(self, value: str | None) -> float | None:
        """Parse float value from NMEA field"""
        if not value or value == "":
            return None

        try:
            return float(value)
        except:
            return None


class NMEAUDPClient:
    """UDP client for NMEA data"""

    def __init__(
        self,
        port: int = DEFAULT_NMEA_UDP_PORT,
        callback: Callable[[NMEAData], None] | None = None,
    ):
        self.port = port
        self.callback = callback
        self.socket = None
        self.running = False
        self.parser = NMEAParser()
        self.last_data: NMEAData | None = None
        self.stale_threshold = 5.0  # seconds
        self._thread: threading.Thread | None = None
        self.logger = logger.bind(component="nmea_udp")

    def start(self):
        """Start NMEA UDP client"""
        if self.running:
            return

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(("", self.port))
            self.socket.settimeout(1.0)

            self.running = True
            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()

            self.logger.info("NMEA UDP client started", port=self.port)

        except Exception as e:
            self.logger.error(
                "Failed to start NMEA UDP client", port=self.port, error=str(e)
            )
            self.stop()

    def stop(self):
        """Stop NMEA UDP client"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        self.logger.info("NMEA UDP client stopped")

    def _listen_loop(self):
        """Main listening loop"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(1024)
                sentence = data.decode("utf-8", errors="ignore").strip()

                if sentence.startswith("$"):
                    nmea_data = self.parser.parse_sentence(sentence)
                    if nmea_data:
                        self.last_data = nmea_data
                        if self.callback:
                            self.callback(nmea_data)

            except TimeoutError:
                continue
            except Exception as e:
                if self.running:
                    self.logger.error("Error in NMEA listening loop", error=str(e))

    def get_current_heading(self) -> float | None:
        """Get current heading if available and not stale"""
        if not self.last_data:
            return None

        if self.last_data.is_stale:
            return None

        return self.last_data.heading_deg_true

    def get_current_position(self) -> tuple | None:
        """Get current position if available and not stale"""
        if not self.last_data:
            return None

        if self.last_data.is_stale:
            return None

        if self.last_data.latitude is not None and self.last_data.longitude is not None:
            return (self.last_data.latitude, self.last_data.longitude)

        return None

    def get_current_velocity(self) -> tuple | None:
        """Get current velocity if available and not stale"""
        if not self.last_data:
            return None

        if self.last_data.is_stale:
            return None

        if (
            self.last_data.speed_over_ground is not None
            and self.last_data.course_over_ground is not None
        ):
            return (self.last_data.speed_over_ground, self.last_data.course_over_ground)

        return None

    def is_data_stale(self) -> bool:
        """Check if NMEA data is stale"""
        if not self.last_data:
            return True

        age = (datetime.now() - self.last_data.timestamp).total_seconds()
        return age > self.stale_threshold
