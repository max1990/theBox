"""
Test JSON parsing functionality.
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from plugins.mara.parser import MARAParser


class TestJSONParsing:
    """Test JSON parsing functionality."""

    def setup_method(self):
        """Setup test method."""
        self.parser = MARAParser()

    def test_basic_json_parsing(self):
        """Test basic JSON parsing."""
        json_data = {
            "timestamp": "2025-01-16T10:30:45.123Z",
            "sensor_id": "EO_001",
            "object_id": "obj_123",
            "confidence": 0.85,
            "bearing_deg": 45.2,
            "elevation_deg": 12.5,
            "range_m": 1500.0,
            "lat": 40.7128,
            "lon": -74.0060,
            "speed_mps": 15.2,
            "heading_deg": 90.0,
            "label": "drone",
            "channel": "EO",
        }

        json_line = str(json_data).replace("'", '"')
        detection = self.parser.autodetect_and_parse(json_line)

        assert detection is not None
        assert detection.source == "mara"
        assert detection.sensor_channel == "EO"
        assert detection.event_type == "DETECTION"
        assert detection.label == "drone"
        assert detection.confidence == 0.85
        assert detection.bearing_deg == 45.2
        assert detection.elev_deg == 12.5
        assert detection.range_km == 1.5  # Converted from meters
        assert detection.lat == 40.7128
        assert detection.lon == -74.0060
        assert detection.speed_mps == 15.2
        assert detection.heading_deg == 90.0

    def test_angle_normalization(self):
        """Test angle normalization."""
        json_data = {
            "timestamp": "2025-01-16T10:30:45.123Z",
            "sensor_id": "EO_001",
            "bearing_deg": 405.0,  # Should normalize to 45.0
            "heading_deg": -90.0,  # Should normalize to 270.0
            "channel": "EO",
        }

        json_line = str(json_data).replace("'", '"')
        detection = self.parser.autodetect_and_parse(json_line)

        assert detection is not None
        assert detection.bearing_deg == 45.0
        assert detection.heading_deg == 270.0

    def test_confidence_scaling(self):
        """Test confidence scaling from percentage."""
        json_data = {
            "timestamp": "2025-01-16T10:30:45.123Z",
            "sensor_id": "EO_001",
            "confidence": 85,  # Should be scaled to 0.85
            "channel": "EO",
        }

        json_line = str(json_data).replace("'", '"')
        detection = self.parser.autodetect_and_parse(json_line)

        assert detection is not None
        assert detection.confidence == 0.85

    def test_channel_normalization(self):
        """Test sensor channel normalization."""
        test_cases = [
            ("EO", "EO"),
            ("electro-optical", "EO"),
            ("VISUAL", "EO"),
            ("camera", "EO"),
            ("IR", "IR"),
            ("infrared", "IR"),
            ("thermal", "IR"),
            ("ACOUSTIC", "ACOUSTIC"),
            ("audio", "ACOUSTIC"),
            ("sound", "ACOUSTIC"),
            ("microphone", "ACOUSTIC"),
            ("unknown", "UNKNOWN"),
            ("", "UNKNOWN"),
        ]

        for input_channel, expected in test_cases:
            json_data = {
                "timestamp": "2025-01-16T10:30:45.123Z",
                "sensor_id": "EO_001",
                "channel": input_channel,
            }

            json_line = str(json_data).replace("'", '"')
            detection = self.parser.autodetect_and_parse(json_line)

            assert detection is not None
            assert detection.sensor_channel == expected

    def test_event_type_detection(self):
        """Test event type detection."""
        # Test heartbeat
        json_data = {
            "timestamp": "2025-01-16T10:30:45.123Z",
            "sensor_id": "EO_001",
            "status": "active",
            "message": "sensor_heartbeat",
            "channel": "EO",
        }

        json_line = str(json_data).replace("'", '"')
        detection = self.parser.autodetect_and_parse(json_line)

        assert detection is not None
        assert detection.event_type == "HEARTBEAT"

        # Test track
        json_data = {
            "timestamp": "2025-01-16T10:30:45.123Z",
            "sensor_id": "EO_001",
            "track_id": "track_001",
            "channel": "EO",
        }

        json_line = str(json_data).replace("'", '"')
        detection = self.parser.autodetect_and_parse(json_line)

        assert detection is not None
        assert detection.event_type == "TRACK"
        assert detection.track_id == "track_001"

    def test_malformed_json(self):
        """Test malformed JSON handling."""
        malformed_json = '{"timestamp": "2025-01-16T10:30:45.123Z", "sensor_id": "EO_001", "confidence": "invalid"'
        detection = self.parser.autodetect_and_parse(malformed_json)
        assert detection is None

    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        json_data = {
            "sensor_id": "EO_001",
            "channel": "EO",
            # Missing timestamp
        }

        json_line = str(json_data).replace("'", '"')
        detection = self.parser.autodetect_and_parse(json_line)

        assert detection is not None
        assert detection.timestamp_utc is not None  # Should use current time
        assert detection.source == "mara"
