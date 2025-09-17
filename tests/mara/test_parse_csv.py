"""
Test CSV parsing functionality.
"""
import pytest
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from plugins.mara.parser import MARAParser


class TestCSVParsing:
    """Test CSV parsing functionality."""
    
    def setup_method(self):
        """Setup test method."""
        self.parser = MARAParser()
    
    def test_basic_csv_parsing(self):
        """Test basic CSV parsing."""
        csv_line = '2025-01-16T10:30:45.123Z,EO_001,obj_123,0.85,45.2,12.5,1500.0,40.7128,-74.0060,15.2,90.0,drone,EO'
        detection = self.parser.autodetect_and_parse(csv_line)
        
        assert detection is not None
        assert detection.source == "mara"
        assert detection.sensor_channel == "EO"
        assert detection.label == "drone"
        assert detection.confidence == 0.85
        assert detection.bearing_deg == 45.2
        assert detection.elev_deg == 12.5
        assert detection.range_km == 1.5  # Converted from meters
        assert detection.lat == 40.7128
        assert detection.lon == -74.0060
        assert detection.speed_mps == 15.2
        assert detection.heading_deg == 90.0
    
    def test_csv_with_quoted_values(self):
        """Test CSV parsing with quoted values."""
        csv_line = '"2025-01-16T10:30:45.123Z","EO_001","obj_123",0.85,45.2,12.5,1500.0,40.7128,-74.0060,15.2,90.0,"drone","EO"'
        detection = self.parser.autodetect_and_parse(csv_line)
        
        assert detection is not None
        assert detection.source == "mara"
        assert detection.sensor_channel == "EO"
        assert detection.label == "drone"
    
    def test_csv_with_missing_values(self):
        """Test CSV parsing with missing values."""
        csv_line = '2025-01-16T10:30:45.123Z,EO_001,obj_123,,45.2,,1500.0,40.7128,-74.0060,15.2,90.0,drone,EO'
        detection = self.parser.autodetect_and_parse(csv_line)
        
        assert detection is not None
        assert detection.source == "mara"
        assert detection.sensor_channel == "EO"
        assert detection.confidence is None  # Missing value
        assert detection.elev_deg is None  # Missing value
        assert detection.bearing_deg == 45.2
    
    def test_csv_confidence_percentage(self):
        """Test confidence percentage conversion in CSV."""
        csv_line = '2025-01-16T10:30:45.123Z,EO_001,obj_123,85,45.2,12.5,1500.0,40.7128,-74.0060,15.2,90.0,drone,EO'
        detection = self.parser.autodetect_and_parse(csv_line)
        
        assert detection is not None
        assert detection.confidence == 0.85
    
    def test_csv_range_conversion(self):
        """Test range conversion from meters to kilometers in CSV."""
        csv_line = '2025-01-16T10:30:45.123Z,EO_001,obj_123,0.85,45.2,12.5,1500.0,40.7128,-74.0060,15.2,90.0,drone,EO'
        detection = self.parser.autodetect_and_parse(csv_line)
        
        assert detection is not None
        assert detection.range_km == 1.5
    
    def test_csv_angle_normalization(self):
        """Test angle normalization in CSV format."""
        csv_line = '2025-01-16T10:30:45.123Z,EO_001,obj_123,0.85,405.0,12.5,1500.0,40.7128,-74.0060,15.2,-90.0,drone,EO'
        detection = self.parser.autodetect_and_parse(csv_line)
        
        assert detection is not None
        assert detection.bearing_deg == 45.0
        assert detection.heading_deg == 270.0
    
    def test_csv_channel_normalization(self):
        """Test sensor channel normalization in CSV."""
        test_cases = [
            ("electro-optical", "EO"),
            ("infrared", "IR"),
            ("acoustic", "ACOUSTIC"),
            ("unknown", "UNKNOWN")
        ]
        
        for input_channel, expected in test_cases:
            csv_line = f'2025-01-16T10:30:45.123Z,EO_001,obj_123,0.85,45.2,12.5,1500.0,40.7128,-74.0060,15.2,90.0,drone,{input_channel}'
            detection = self.parser.autodetect_and_parse(csv_line)
            
            assert detection is not None
            assert detection.sensor_channel == expected
    
    def test_csv_invalid_values(self):
        """Test handling of invalid values in CSV."""
        csv_line = '2025-01-16T10:30:45.123Z,EO_001,obj_123,invalid,not_a_number,12.5,1500.0,40.7128,-74.0060,15.2,90.0,drone,EO'
        detection = self.parser.autodetect_and_parse(csv_line)
        
        assert detection is not None
        assert detection.confidence is None
        assert detection.bearing_deg is None
        assert detection.elev_deg == 12.5  # Valid value
    
    def test_csv_short_line(self):
        """Test CSV line with fewer columns than expected."""
        csv_line = '2025-01-16T10:30:45.123Z,EO_001,obj_123,0.85'
        detection = self.parser.autodetect_and_parse(csv_line)
        
        assert detection is not None
        assert detection.source == "mara"
        assert detection.confidence == 0.85
        # Other fields should be None or default values
    
    def test_csv_long_line(self):
        """Test CSV line with more columns than expected."""
        csv_line = '2025-01-16T10:30:45.123Z,EO_001,obj_123,0.85,45.2,12.5,1500.0,40.7128,-74.0060,15.2,90.0,drone,EO,extra1,extra2,extra3'
        detection = self.parser.autodetect_and_parse(csv_line)
        
        assert detection is not None
        assert detection.source == "mara"
        assert detection.sensor_channel == "EO"
        # Extra columns should be ignored
    
    def test_csv_empty_line(self):
        """Test empty CSV line."""
        detection = self.parser.autodetect_and_parse("")
        assert detection is None
    
    def test_csv_no_commas(self):
        """Test line without commas (not CSV)."""
        detection = self.parser.autodetect_and_parse("this is not csv format")
        assert detection is None
