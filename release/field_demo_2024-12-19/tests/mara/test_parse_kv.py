"""
Test key=value parsing functionality.
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from plugins.mara.parser import MARAParser


class TestKeyValueParsing:
    """Test key=value parsing functionality."""

    def setup_method(self):
        """Setup test method."""
        self.parser = MARAParser()

    def test_basic_kv_parsing(self):
        """Test basic key=value parsing."""
        kv_line = "timestamp=2025-01-16T10:30:45.123Z sensor_id=EO_001 object_id=obj_123 confidence=0.85 bearing_deg=45.2 channel=EO"
        detection = self.parser.autodetect_and_parse(kv_line)

        assert detection is not None
        assert detection.source == "mara"
        assert detection.sensor_channel == "EO"
        assert detection.confidence == 0.85
        assert detection.bearing_deg == 45.2

    def test_kv_with_quoted_values(self):
        """Test key=value parsing with quoted values."""
        kv_line = 'timestamp="2025-01-16T10:30:45.123Z" sensor_id="EO_001" label="drone" channel="EO"'
        detection = self.parser.autodetect_and_parse(kv_line)

        assert detection is not None
        assert detection.source == "mara"
        assert detection.sensor_channel == "EO"
        assert detection.label == "drone"

    def test_kv_with_single_quotes(self):
        """Test key=value parsing with single quotes."""
        kv_line = "timestamp='2025-01-16T10:30:45.123Z' sensor_id='EO_001' channel='IR'"
        detection = self.parser.autodetect_and_parse(kv_line)

        assert detection is not None
        assert detection.source == "mara"
        assert detection.sensor_channel == "IR"

    def test_kv_confidence_percentage(self):
        """Test confidence percentage conversion."""
        kv_line = "timestamp=2025-01-16T10:30:45.123Z sensor_id=EO_001 confidence=85 channel=EO"
        detection = self.parser.autodetect_and_parse(kv_line)

        assert detection is not None
        assert detection.confidence == 0.85

    def test_kv_range_conversion(self):
        """Test range conversion from meters to kilometers."""
        kv_line = "timestamp=2025-01-16T10:30:45.123Z sensor_id=EO_001 range_m=1500.0 channel=EO"
        detection = self.parser.autodetect_and_parse(kv_line)

        assert detection is not None
        assert detection.range_km == 1.5

    def test_kv_angle_normalization(self):
        """Test angle normalization in key=value format."""
        kv_line = "timestamp=2025-01-16T10:30:45.123Z sensor_id=EO_001 bearing_deg=405.0 heading_deg=-90.0 channel=EO"
        detection = self.parser.autodetect_and_parse(kv_line)

        assert detection is not None
        assert detection.bearing_deg == 45.0
        assert detection.heading_deg == 270.0

    def test_kv_elevation_clamping(self):
        """Test elevation clamping."""
        kv_line = "timestamp=2025-01-16T10:30:45.123Z sensor_id=EO_001 elevation_deg=95.0 channel=EO"
        detection = self.parser.autodetect_and_parse(kv_line)

        assert detection is not None
        assert detection.elev_deg == 90.0  # Clamped to max elevation

    def test_kv_latitude_clamping(self):
        """Test latitude clamping."""
        kv_line = (
            "timestamp=2025-01-16T10:30:45.123Z sensor_id=EO_001 lat=95.0 channel=EO"
        )
        detection = self.parser.autodetect_and_parse(kv_line)

        assert detection is not None
        assert detection.lat == 90.0  # Clamped to max latitude

    def test_kv_longitude_clamping(self):
        """Test longitude clamping."""
        kv_line = (
            "timestamp=2025-01-16T10:30:45.123Z sensor_id=EO_001 lon=185.0 channel=EO"
        )
        detection = self.parser.autodetect_and_parse(kv_line)

        assert detection is not None
        assert detection.lon == 180.0  # Clamped to max longitude

    def test_kv_speed_clamping(self):
        """Test speed clamping."""
        kv_line = "timestamp=2025-01-16T10:30:45.123Z sensor_id=EO_001 speed_mps=1500.0 channel=EO"
        detection = self.parser.autodetect_and_parse(kv_line)

        assert detection is not None
        assert detection.speed_mps == 1000.0  # Clamped to max speed

    def test_kv_invalid_values(self):
        """Test handling of invalid values."""
        kv_line = "timestamp=2025-01-16T10:30:45.123Z sensor_id=EO_001 confidence=invalid bearing_deg=not_a_number channel=EO"
        detection = self.parser.autodetect_and_parse(kv_line)

        assert detection is not None
        assert detection.confidence is None
        assert detection.bearing_deg is None

    def test_kv_empty_line(self):
        """Test empty key=value line."""
        detection = self.parser.autodetect_and_parse("")
        assert detection is None

    def test_kv_no_equals(self):
        """Test line without equals signs."""
        detection = self.parser.autodetect_and_parse("this is not key value format")
        assert detection is None
