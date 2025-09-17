"""
Unit tests for NMEA parser
"""

import unittest
from datetime import datetime, timezone

from plugins.dspnor.nmea_ingest import NMEAParser, NMEAUDPClient


class TestNMEAParser(unittest.TestCase):
    """Test NMEA parser"""
    
    def setUp(self):
        self.parser = NMEAParser()
    
    def test_validate_checksum_valid(self):
        """Test valid checksum validation"""
        sentence = "$GPRMC,123456.00,A,4000.0000,N,07400.0000,W,0.0,0.0,010120,0.0,E*6A"
        result = self.parser._validate_checksum(sentence)
        self.assertTrue(result)
    
    def test_validate_checksum_invalid(self):
        """Test invalid checksum validation"""
        sentence = "$GPRMC,123456.00,A,4000.0000,N,07400.0000,W,0.0,0.0,010120,0.0,E*6B"
        result = self.parser._validate_checksum(sentence)
        self.assertFalse(result)
    
    def test_validate_checksum_no_checksum(self):
        """Test validation with no checksum"""
        sentence = "$GPRMC,123456.00,A,4000.0000,N,07400.0000,W,0.0,0.0,010120,0.0,E"
        result = self.parser._validate_checksum(sentence)
        self.assertTrue(result)  # Should pass if no checksum
    
    def test_parse_rmc_valid(self):
        """Test parsing valid RMC sentence"""
        sentence = "$GPRMC,123456.00,A,4000.0000,N,07400.0000,W,0.0,0.0,010120,0.0,E*6A"
        result = self.parser.parse_sentence(sentence)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.heading_deg_true, 0.0)
        self.assertEqual(result.course_over_ground, 0.0)
        self.assertEqual(result.speed_over_ground, 0.0)
        self.assertEqual(result.latitude, 40.0)
        self.assertEqual(result.longitude, -74.0)
    
    def test_parse_rmc_invalid_checksum(self):
        """Test parsing RMC with invalid checksum"""
        sentence = "$GPRMC,123456.00,A,4000.0000,N,07400.0000,W,0.0,0.0,010120,0.0,E*6B"
        result = self.parser.parse_sentence(sentence)
        
        self.assertIsNone(result)
    
    def test_parse_rmc_short(self):
        """Test parsing RMC with insufficient fields"""
        sentence = "$GPRMC,123456.00,A"
        result = self.parser.parse_sentence(sentence)
        
        self.assertIsNone(result)
    
    def test_parse_vtg_valid(self):
        """Test parsing valid VTG sentence"""
        sentence = "$GPVTG,45.0,T,45.0,M,10.0,N,18.5,K*4D"
        result = self.parser.parse_sentence(sentence)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.heading_deg_true, 45.0)
        self.assertEqual(result.course_over_ground, 45.0)
        self.assertAlmostEqual(result.speed_over_ground, 5.14, places=1)  # 10 knots to m/s
    
    def test_parse_gga_valid(self):
        """Test parsing valid GGA sentence"""
        sentence = "$GPGGA,123456.00,4000.0000,N,07400.0000,W,1,8,1.0,100.0,M,0.0,M,,*4A"
        result = self.parser.parse_sentence(sentence)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.latitude, 40.0)
        self.assertEqual(result.longitude, -74.0)
        self.assertEqual(result.altitude, 100.0)
    
    def test_parse_hdg_valid(self):
        """Test parsing valid HDG sentence"""
        sentence = "$GPHDG,45.0,2.0,3.0*4A"
        result = self.parser.parse_sentence(sentence)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.heading_deg_true, 50.0)  # 45 + 2 + 3
    
    def test_parse_unsupported_sentence(self):
        """Test parsing unsupported sentence type"""
        sentence = "$GPGLL,4000.0000,N,07400.0000,W,123456.00,A*4A"
        result = self.parser.parse_sentence(sentence)
        
        self.assertIsNone(result)
    
    def test_parse_timestamp_with_milliseconds(self):
        """Test timestamp parsing with milliseconds"""
        timestamp = self.parser._parse_timestamp("123456.789")
        
        self.assertEqual(timestamp.hour, 12)
        self.assertEqual(timestamp.minute, 34)
        self.assertEqual(timestamp.second, 56)
        self.assertEqual(timestamp.microsecond, 789000)
    
    def test_parse_timestamp_without_milliseconds(self):
        """Test timestamp parsing without milliseconds"""
        timestamp = self.parser._parse_timestamp("123456")
        
        self.assertEqual(timestamp.hour, 12)
        self.assertEqual(timestamp.minute, 34)
        self.assertEqual(timestamp.second, 56)
        self.assertEqual(timestamp.microsecond, 0)
    
    def test_parse_timestamp_with_date(self):
        """Test timestamp parsing with date"""
        timestamp = self.parser._parse_timestamp("123456", "010120")
        
        self.assertEqual(timestamp.year, 2020)
        self.assertEqual(timestamp.month, 1)
        self.assertEqual(timestamp.day, 1)
        self.assertEqual(timestamp.hour, 12)
        self.assertEqual(timestamp.minute, 34)
        self.assertEqual(timestamp.second, 56)
    
    def test_parse_latitude_north(self):
        """Test latitude parsing for north"""
        lat = self.parser._parse_latitude("4000.0000", "N")
        
        self.assertEqual(lat, 40.0)
    
    def test_parse_latitude_south(self):
        """Test latitude parsing for south"""
        lat = self.parser._parse_latitude("4000.0000", "S")
        
        self.assertEqual(lat, -40.0)
    
    def test_parse_longitude_east(self):
        """Test longitude parsing for east"""
        lon = self.parser._parse_longitude("07400.0000", "E")
        
        self.assertEqual(lon, 74.0)
    
    def test_parse_longitude_west(self):
        """Test longitude parsing for west"""
        lon = self.parser._parse_longitude("07400.0000", "W")
        
        self.assertEqual(lon, -74.0)
    
    def test_parse_float_valid(self):
        """Test float parsing with valid input"""
        value = self.parser._parse_float("123.45")
        
        self.assertEqual(value, 123.45)
    
    def test_parse_float_invalid(self):
        """Test float parsing with invalid input"""
        value = self.parser._parse_float("invalid")
        
        self.assertIsNone(value)
    
    def test_parse_float_empty(self):
        """Test float parsing with empty input"""
        value = self.parser._parse_float("")
        
        self.assertIsNone(value)


class TestNMEAUDPClient(unittest.TestCase):
    """Test NMEA UDP client"""
    
    def setUp(self):
        self.client = NMEAUDPClient(port=12345)
        self.received_data = None
    
    def test_callback_setting(self):
        """Test callback setting"""
        callback = lambda data: setattr(self, 'received_data', data)
        self.client.callback = callback
        
        # Simulate receiving data
        nmea_data = type('NMEAData', (), {
            'heading_deg_true': 45.0,
            'timestamp': datetime.now(timezone.utc)
        })()
        
        self.client.callback(nmea_data)
        self.assertEqual(self.received_data, nmea_data)
    
    def test_get_current_heading_no_data(self):
        """Test getting current heading with no data"""
        heading = self.client.get_current_heading()
        
        self.assertIsNone(heading)
    
    def test_get_current_heading_stale_data(self):
        """Test getting current heading with stale data"""
        # Create stale data
        stale_time = datetime.now(timezone.utc).replace(year=2020)
        nmea_data = type('NMEAData', (), {
            'heading_deg_true': 45.0,
            'timestamp': stale_time,
            'is_stale': True
        })()
        
        self.client.last_data = nmea_data
        heading = self.client.get_current_heading()
        
        self.assertIsNone(heading)
    
    def test_get_current_heading_valid_data(self):
        """Test getting current heading with valid data"""
        nmea_data = type('NMEAData', (), {
            'heading_deg_true': 45.0,
            'timestamp': datetime.now(timezone.utc),
            'is_stale': False
        })()
        
        self.client.last_data = nmea_data
        heading = self.client.get_current_heading()
        
        self.assertEqual(heading, 45.0)
    
    def test_get_current_position_no_data(self):
        """Test getting current position with no data"""
        position = self.client.get_current_position()
        
        self.assertIsNone(position)
    
    def test_get_current_position_valid_data(self):
        """Test getting current position with valid data"""
        nmea_data = type('NMEAData', (), {
            'latitude': 40.0,
            'longitude': -74.0,
            'timestamp': datetime.now(timezone.utc),
            'is_stale': False
        })()
        
        self.client.last_data = nmea_data
        position = self.client.get_current_position()
        
        self.assertEqual(position, (40.0, -74.0))
    
    def test_get_current_velocity_no_data(self):
        """Test getting current velocity with no data"""
        velocity = self.client.get_current_velocity()
        
        self.assertIsNone(velocity)
    
    def test_get_current_velocity_valid_data(self):
        """Test getting current velocity with valid data"""
        nmea_data = type('NMEAData', (), {
            'speed_over_ground': 10.0,
            'course_over_ground': 45.0,
            'timestamp': datetime.now(timezone.utc),
            'is_stale': False
        })()
        
        self.client.last_data = nmea_data
        velocity = self.client.get_current_velocity()
        
        self.assertEqual(velocity, (10.0, 45.0))
    
    def test_is_data_stale_no_data(self):
        """Test stale check with no data"""
        is_stale = self.client.is_data_stale()
        
        self.assertTrue(is_stale)
    
    def test_is_data_stale_recent_data(self):
        """Test stale check with recent data"""
        nmea_data = type('NMEAData', (), {
            'timestamp': datetime.now(timezone.utc)
        })()
        
        self.client.last_data = nmea_data
        is_stale = self.client.is_data_stale()
        
        self.assertFalse(is_stale)
    
    def test_is_data_stale_old_data(self):
        """Test stale check with old data"""
        old_time = datetime.now(timezone.utc).replace(year=2020)
        nmea_data = type('NMEAData', (), {
            'timestamp': old_time
        })()
        
        self.client.last_data = nmea_data
        is_stale = self.client.is_data_stale()
        
        self.assertTrue(is_stale)


if __name__ == '__main__':
    unittest.main()
