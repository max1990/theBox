"""
Test format autodetection functionality.
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from plugins.mara.parser import MARAParser


class TestFormatAutodetect:
    """Test format autodetection."""

    def setup_method(self):
        """Setup test method."""
        self.parser = MARAParser()

    def test_json_detection(self):
        """Test JSON format detection."""
        json_line = '{"timestamp": "2025-01-16T10:30:45.123Z", "sensor_id": "EO_001", "confidence": 0.85}'
        detection = self.parser.autodetect_and_parse(json_line)
        assert detection is not None
        assert detection.source == "mara"
        assert detection.sensor_channel == "UNKNOWN"  # No channel specified

    def test_key_value_detection(self):
        """Test key=value format detection."""
        kv_line = "timestamp=2025-01-16T10:30:45.123Z sensor_id=EO_001 confidence=0.85 channel=EO"
        detection = self.parser.autodetect_and_parse(kv_line)
        assert detection is not None
        assert detection.source == "mara"
        assert detection.sensor_channel == "EO"

    def test_csv_detection(self):
        """Test CSV format detection."""
        csv_line = "2025-01-16T10:30:45.123Z,EO_001,obj_123,0.85,45.2,12.5,1500.0,40.7128,-74.0060,15.2,90.0,drone,EO"
        detection = self.parser.autodetect_and_parse(csv_line)
        assert detection is not None
        assert detection.source == "mara"
        assert detection.sensor_channel == "EO"
        assert detection.label == "drone"

    def test_unknown_format(self):
        """Test unknown format handling."""
        unknown_line = "This is not a recognized format"
        detection = self.parser.autodetect_and_parse(unknown_line)
        assert detection is None

    def test_empty_line(self):
        """Test empty line handling."""
        detection = self.parser.autodetect_and_parse("")
        assert detection is None

        detection = self.parser.autodetect_and_parse("   ")
        assert detection is None

    def test_comment_line(self):
        """Test comment line handling."""
        comment_line = "# This is a comment"
        detection = self.parser.autodetect_and_parse(comment_line)
        assert detection is None
