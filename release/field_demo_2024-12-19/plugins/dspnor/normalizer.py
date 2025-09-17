"""
Detection normalizer for Dspnor plugin
"""

import math
from datetime import datetime, timezone
from typing import Any

import structlog

from .constants import M_TO_KM, MPS_TO_KTS
from .schemas import CAT010Track, NMEAData, NormalizedDetection

logger = structlog.get_logger(__name__)


class DetectionNormalizer:
    """Normalize CAT-010 tracks to TheBox detection format"""

    def __init__(
        self,
        conf_map: str = "snr_db:linear:0:30",
        min_conf: float = 0.05,
        max_conf: float = 0.99,
        range_units: str = "km",
        speed_units: str = "mps",
        bearing_is_relative: bool = False,
    ):
        self.conf_map = conf_map
        self.min_conf = min_conf
        self.max_conf = max_conf
        self.range_units = range_units
        self.speed_units = speed_units
        self.bearing_is_relative = bearing_is_relative
        self.logger = logger.bind(component="normalizer")

        # Parse confidence mapping
        self.conf_mapping = self._parse_conf_map(conf_map)

    def normalize(
        self,
        track: CAT010Track,
        current_heading: float | None = None,
        nmea_data: NMEAData | None = None,
    ) -> NormalizedDetection | None:
        """Normalize CAT-010 track to detection format"""
        try:
            # Generate object ID
            object_id = self._generate_object_id(track)

            # Extract position and convert to bearing/distance
            bearing, distance = self._extract_position(track, current_heading)
            if bearing is None:
                self.logger.warning(
                    "No position data available for track", track_id=object_id
                )
                return None

            # Extract velocity
            speed, course = self._extract_velocity(track)

            # Calculate confidence
            confidence = self._calculate_confidence(track)

            # Convert units
            distance_m = self._convert_distance(distance) if distance else None
            speed_mps = self._convert_speed(speed) if speed else None

            # Calculate errors
            bearing_error = self._calculate_bearing_error(track)
            distance_error = self._calculate_distance_error(track, distance_m)

            # Create normalized detection
            detection = NormalizedDetection(
                object_id=object_id,
                time_utc=self._get_timestamp(track),
                bearing_deg_true=bearing,
                bearing_error_deg=bearing_error,
                distance_m=distance_m,
                distance_error_m=distance_error,
                altitude_m=0.0,  # CAT-010 doesn't provide altitude
                altitude_error_m=20.0,
                speed_mps=speed_mps,
                course_deg=course,
                confidence=confidence,
                track_id=str(track.track_number) if track.track_number else None,
                has_mmsi=track.has_mmsi,
                raw_data=self._create_raw_data(track, nmea_data),
            )

            return detection

        except Exception as e:
            self.logger.error("Failed to normalize track", error=str(e))
            return None

    def _generate_object_id(self, track: CAT010Track) -> str:
        """Generate unique object ID for track"""
        if track.track_number is not None:
            return f"dspnor_{track.track_number:06d}"
        elif track.target_address is not None:
            return f"dspnor_{track.target_address:06x}"
        else:
            # Fallback to hash of available data
            data_str = f"{track.time_of_day}_{track.target_id}_{track.has_mmsi}"
            return f"dspnor_{hash(data_str) & 0xFFFFFF:06x}"

    def _extract_position(
        self, track: CAT010Track, current_heading: float | None
    ) -> tuple[float | None, float | None]:
        """Extract bearing and distance from track position"""
        # Try polar position first
        if track.position_polar:
            range_m, bearing_deg = track.position_polar
            distance = range_m
        # Try cartesian position
        elif track.position_cartesian:
            x, y = track.position_cartesian
            distance = math.sqrt(x * x + y * y)
            bearing_deg = math.degrees(math.atan2(x, y))
        else:
            return None, None

        # Convert to true bearing if needed
        if not self.bearing_is_relative and current_heading is not None:
            bearing_deg = (bearing_deg + current_heading) % 360

        return bearing_deg, distance

    def _extract_velocity(
        self, track: CAT010Track
    ) -> tuple[float | None, float | None]:
        """Extract speed and course from track velocity"""
        # Try polar velocity first
        if track.velocity_polar:
            speed, course = track.velocity_polar
            return speed, course
        # Try cartesian velocity
        elif track.velocity_cartesian:
            vx, vy = track.velocity_cartesian
            speed = math.sqrt(vx * vx + vy * vy)
            course = math.degrees(math.atan2(vx, vy))
            return speed, course
        # Try ground speed
        elif track.ground_speed is not None:
            return track.ground_speed, None
        else:
            return None, None

    def _calculate_confidence(self, track: CAT010Track) -> int:
        """Calculate confidence score for track"""
        try:
            # Start with base confidence
            confidence = 50

            # Boost for track quality
            if track.track_quality is not None:
                quality_boost = min(track.track_quality * 5, 30)
                confidence += quality_boost

            # Boost for MMSI identification
            if track.has_mmsi:
                confidence += 20

            # Boost for target ID
            if track.target_id:
                confidence += 10

            # Apply confidence mapping if configured
            if self.conf_mapping:
                mapped_conf = self._apply_conf_mapping(track)
                if mapped_conf is not None:
                    confidence = mapped_conf

            # Clamp to valid range
            confidence = max(self.min_conf * 100, min(self.max_conf * 100, confidence))

            return int(confidence)

        except Exception as e:
            self.logger.error("Error calculating confidence", error=str(e))
            return 75  # Default confidence

    def _apply_conf_mapping(self, track: CAT010Track) -> float | None:
        """Apply confidence mapping to track"""
        if not self.conf_mapping:
            return None

        source_field, mapping_type, lo, hi = self.conf_mapping

        # Get source value (placeholder - would need actual SNR data)
        source_value = 15.0  # Default SNR

        if mapping_type == "linear":
            # Linear mapping from [lo, hi] to [0, 1]
            if hi > lo:
                normalized = (source_value - lo) / (hi - lo)
                return max(0.0, min(1.0, normalized))

        return None

    def _calculate_bearing_error(self, track: CAT010Track) -> float:
        """Calculate bearing error in degrees"""
        # Base error on track quality
        if track.track_quality is not None:
            # Higher quality = lower error
            return max(1.0, 10.0 - (track.track_quality * 0.5))

        return 5.0  # Default bearing error

    def _calculate_distance_error(
        self, track: CAT010Track, distance_m: float | None
    ) -> float | None:
        """Calculate distance error in meters"""
        if distance_m is None:
            return None

        # Base error on distance (percentage)
        return max(50.0, distance_m * 0.1)  # 10% of distance, minimum 50m

    def _get_timestamp(self, track: CAT010Track) -> datetime:
        """Get timestamp for track"""
        if track.time_of_day is not None:
            # Convert time of day to UTC timestamp
            # This is a simplified conversion - in practice you'd need
            # to know the date and handle day rollover
            now = datetime.now(timezone.utc)
            tod_seconds = track.time_of_day
            hours = int(tod_seconds // 3600)
            minutes = int((tod_seconds % 3600) // 60)
            seconds = tod_seconds % 60

            return now.replace(
                hour=hours,
                minute=minutes,
                second=int(seconds),
                microsecond=int((seconds % 1) * 1000000),
            )
        else:
            return datetime.now(timezone.utc)

    def _convert_distance(self, distance: float) -> float:
        """Convert distance to target units"""
        if self.range_units == "km":
            return distance * M_TO_KM
        else:  # meters
            return distance

    def _convert_speed(self, speed: float) -> float:
        """Convert speed to target units"""
        if self.speed_units == "kts":
            return speed * MPS_TO_KTS
        else:  # m/s
            return speed

    def _create_raw_data(
        self, track: CAT010Track, nmea_data: NMEAData | None
    ) -> dict[str, Any]:
        """Create raw data dictionary"""
        raw_data = {
            "track_number": track.track_number,
            "target_address": track.target_address,
            "track_quality": track.track_quality,
            "target_id": track.target_id,
            "has_mmsi": track.has_mmsi,
            "mode_3a_code": track.mode_3a_code,
            "time_of_day": track.time_of_day,
        }

        if track.position_polar:
            raw_data["position_polar"] = {
                "range_m": track.position_polar[0],
                "bearing_deg": track.position_polar[1],
            }

        if track.position_cartesian:
            raw_data["position_cartesian"] = {
                "x_m": track.position_cartesian[0],
                "y_m": track.position_cartesian[1],
            }

        if track.velocity_polar:
            raw_data["velocity_polar"] = {
                "speed_mps": track.velocity_polar[0],
                "heading_deg": track.velocity_polar[1],
            }

        if track.velocity_cartesian:
            raw_data["velocity_cartesian"] = {
                "vx_mps": track.velocity_cartesian[0],
                "vy_mps": track.velocity_cartesian[1],
            }

        if nmea_data:
            raw_data["nmea"] = {
                "heading_deg_true": nmea_data.heading_deg_true,
                "course_over_ground": nmea_data.course_over_ground,
                "speed_over_ground": nmea_data.speed_over_ground,
                "latitude": nmea_data.latitude,
                "longitude": nmea_data.longitude,
            }

        return raw_data

    def _parse_conf_map(self, conf_map: str) -> tuple[str, str, float, float] | None:
        """Parse confidence mapping string"""
        try:
            parts = conf_map.split(":")
            if len(parts) != 4:
                return None

            source_field = parts[0]
            mapping_type = parts[1]
            lo = float(parts[2])
            hi = float(parts[3])

            return (source_field, mapping_type, lo, hi)

        except:
            return None
