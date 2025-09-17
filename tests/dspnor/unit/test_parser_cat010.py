"""
Unit tests for CAT-010 parser
"""

import unittest
import struct
from unittest.mock import patch

from plugins.dspnor.parser_cat010 import CAT010Parser
from plugins.dspnor.constants import (
    CAT010_ITEM_140, CAT010_ITEM_161, CAT010_ITEM_041, CAT010_ITEM_042,
    CAT010_ITEM_200, CAT010_ITEM_202, CAT010_ITEM_220, CAT010_ITEM_245
)


class TestCAT010Parser(unittest.TestCase):
    """Test CAT-010 parser"""
    
    def setUp(self):
        self.parser = CAT010Parser()
    
    def test_parse_invalid_message_too_short(self):
        """Test parsing message that's too short"""
        data = b"\x0A"  # Just CAT identifier
        result = self.parser.parse(data)
        self.assertIsNone(result)
    
    def test_parse_invalid_message_wrong_cat(self):
        """Test parsing message with wrong CAT identifier"""
        data = b"\x0B\x00\x10"  # Wrong CAT identifier
        result = self.parser.parse(data)
        self.assertIsNone(result)
    
    def test_parse_message_length_mismatch(self):
        """Test parsing message with length mismatch"""
        data = b"\x0A\x00\x20"  # Length says 32 bytes, but only 3 provided
        result = self.parser.parse(data)
        self.assertIsNone(result)
    
    def test_parse_minimal_message(self):
        """Test parsing minimal valid message"""
        # CAT-010 with minimal FSPEC (just length)
        data = b"\x0A\x00\x05\x00"  # CAT=10, LEN=5, FSPEC=00 (terminated)
        result = self.parser.parse(data)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, type(self.parser).__module__ + '.CAT010Track')
    
    def test_parse_time_of_day(self):
        """Test parsing time of day item"""
        # Create message with I010/140 (Time of Day)
        fspec = struct.pack('B', 0x80)  # FSPEC with bit 1 set
        tod_data = struct.pack('>I', 3600 * 128)[1:]  # 1 hour in 1/128 seconds
        
        data = b"\x0A" + struct.pack('>H', 3 + len(fspec) + len(tod_data)) + fspec + tod_data
        result = self.parser.parse(data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.time_of_day, 3600.0)  # 1 hour
    
    def test_parse_track_number(self):
        """Test parsing track number item"""
        # Create message with I010/161 (Track Number)
        fspec = struct.pack('B', 0x40)  # FSPEC with bit 2 set
        track_num_data = struct.pack('>H', 12345)
        
        data = b"\x0A" + struct.pack('>H', 3 + len(fspec) + len(track_num_data)) + fspec + track_num_data
        result = self.parser.parse(data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.track_number, 12345)
    
    def test_parse_target_address(self):
        """Test parsing target address item"""
        # Create message with I010/041 (Target Address)
        fspec = struct.pack('B', 0x20)  # FSPEC with bit 3 set
        addr_data = struct.pack('>I', 0x123456)[1:]  # 3-byte address
        
        data = b"\x0A" + struct.pack('>H', 3 + len(fspec) + len(addr_data)) + fspec + addr_data
        result = self.parser.parse(data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.target_address, 0x123456)
    
    def test_parse_track_quality(self):
        """Test parsing track quality item"""
        # Create message with I010/042 (Track Quality)
        fspec = struct.pack('B', 0x10)  # FSPEC with bit 4 set
        quality_data = struct.pack('B', 85)  # Quality value
        
        data = b"\x0A" + struct.pack('>H', 3 + len(fspec) + len(quality_data)) + fspec + quality_data
        result = self.parser.parse(data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.track_quality, 85)
    
    def test_parse_ground_speed(self):
        """Test parsing ground speed item"""
        # Create message with I010/200 (Ground Speed)
        fspec = struct.pack('B', 0x08)  # FSPEC with bit 5 set
        speed_data = struct.pack('>H', 100)  # 100 * 0.25 = 25 m/s
        
        data = b"\x0A" + struct.pack('>H', 3 + len(fspec) + len(speed_data)) + fspec + speed_data
        result = self.parser.parse(data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.ground_speed, 25.0)
    
    def test_parse_track_angle_rate(self):
        """Test parsing track angle rate item"""
        # Create message with I010/202 (Track Angle Rate)
        fspec = struct.pack('B', 0x04)  # FSPEC with bit 6 set
        rate_data = struct.pack('>h', 100)  # 100 * 0.01 = 1.0 deg/s
        
        data = b"\x0A" + struct.pack('>H', 3 + len(fspec) + len(rate_data)) + fspec + rate_data
        result = self.parser.parse(data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.track_angle_rate, 1.0)
    
    def test_parse_mode_3a_code(self):
        """Test parsing Mode 3/A code item"""
        # Create message with I010/220 (Mode 3/A Code)
        fspec = struct.pack('B', 0x02)  # FSPEC with bit 7 set
        code_data = struct.pack('>H', 0x1234)
        
        data = b"\x0A" + struct.pack('>H', 3 + len(fspec) + len(code_data)) + fspec + code_data
        result = self.parser.parse(data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.mode_3a_code, 0x1234)
    
    def test_parse_target_identification(self):
        """Test parsing target identification item"""
        # Create message with I010/245 (Target Identification)
        fspec = struct.pack('B', 0x01)  # FSPEC with bit 8 set
        id_data = b"TESTID"  # 6-byte ID
        
        data = b"\x0A" + struct.pack('>H', 3 + len(fspec) + len(id_data)) + fspec + id_data
        result = self.parser.parse(data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.target_id, "TESTID")
    
    def test_parse_target_identification_with_mmsi(self):
        """Test parsing target identification with MMSI bit set"""
        # Create message with I010/245 (Target Identification) with MMSI bit
        fspec = struct.pack('B', 0x01)  # FSPEC with bit 8 set
        id_data = b"TESTID"  # 6-byte ID
        id_data = id_data[:1] + bytes([id_data[1] | 0x40]) + id_data[2:]  # Set MMSI bit
        
        data = b"\x0A" + struct.pack('>H', 3 + len(fspec) + len(id_data)) + fspec + id_data
        result = self.parser.parse(data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.target_id, "TESTID")
        self.assertTrue(result.has_mmsi)
    
    def test_parse_multiple_items(self):
        """Test parsing message with multiple items"""
        # Create message with multiple items
        fspec = struct.pack('B', 0xE0)  # FSPEC with bits 1, 2, 3 set
        tod_data = struct.pack('>I', 3600 * 128)[1:]  # Time of day
        track_data = struct.pack('>H', 12345)  # Track number
        addr_data = struct.pack('>I', 0x123456)[1:]  # Target address
        
        data = b"\x0A" + struct.pack('>H', 3 + len(fspec) + len(tod_data) + len(track_data) + len(addr_data)) + fspec + tod_data + track_data + addr_data
        result = self.parser.parse(data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.time_of_day, 3600.0)
        self.assertEqual(result.track_number, 12345)
        self.assertEqual(result.target_address, 0x123456)
    
    def test_extract_position_polar(self):
        """Test position extraction from polar coordinates"""
        track = type('Track', (), {
            'position_polar': (1000.0, 45.0),  # 1000m at 45 degrees
            'position_cartesian': None
        })()
        
        position = self.parser.extract_position(track)
        self.assertEqual(position, (1000.0, 45.0))
    
    def test_extract_position_cartesian(self):
        """Test position extraction from cartesian coordinates"""
        track = type('Track', (), {
            'position_polar': None,
            'position_cartesian': (100.0, 200.0)  # x, y in meters
        })()
        
        position = self.parser.extract_position(track)
        self.assertIsNotNone(position)
        # Should convert to polar
        import math
        expected_range = math.sqrt(100*100 + 200*200)
        expected_bearing = math.degrees(math.atan2(100, 200))
        self.assertAlmostEqual(position[0], expected_range, places=1)
        self.assertAlmostEqual(position[1], expected_bearing, places=1)
    
    def test_extract_velocity_polar(self):
        """Test velocity extraction from polar coordinates"""
        track = type('Track', (), {
            'velocity_polar': (25.0, 90.0),  # 25 m/s at 90 degrees
            'velocity_cartesian': None,
            'ground_speed': None
        })()
        
        velocity = self.parser.extract_velocity(track)
        self.assertEqual(velocity, (25.0, 90.0))
    
    def test_extract_velocity_ground_speed(self):
        """Test velocity extraction from ground speed"""
        track = type('Track', (), {
            'velocity_polar': None,
            'velocity_cartesian': None,
            'ground_speed': 30.0
        })()
        
        velocity = self.parser.extract_velocity(track)
        self.assertEqual(velocity, (30.0, 0.0))
    
    def test_get_track_id_from_number(self):
        """Test track ID generation from track number"""
        track = type('Track', (), {
            'track_number': 12345,
            'target_address': None
        })()
        
        track_id = self.parser.get_track_id(track)
        self.assertEqual(track_id, "dspnor_track_12345")
    
    def test_get_track_id_from_address(self):
        """Test track ID generation from target address"""
        track = type('Track', (), {
            'track_number': None,
            'target_address': 0x123456
        })()
        
        track_id = self.parser.get_track_id(track)
        self.assertEqual(track_id, "dspnor_addr_123456")
    
    def test_get_track_id_fallback(self):
        """Test track ID generation fallback"""
        track = type('Track', (), {
            'track_number': None,
            'target_address': None
        })()
        
        track_id = self.parser.get_track_id(track)
        self.assertTrue(track_id.startswith("dspnor_unknown_"))
    
    def test_is_valid_track_with_number(self):
        """Test track validation with track number"""
        track = type('Track', (), {
            'track_number': 12345,
            'target_address': None,
            'position_polar': None,
            'position_cartesian': None
        })()
        
        self.assertTrue(self.parser.is_valid_track(track))
    
    def test_is_valid_track_with_address(self):
        """Test track validation with target address"""
        track = type('Track', (), {
            'track_number': None,
            'target_address': 0x123456,
            'position_polar': None,
            'position_cartesian': None
        })()
        
        self.assertTrue(self.parser.is_valid_track(track))
    
    def test_is_valid_track_with_position(self):
        """Test track validation with position"""
        track = type('Track', (), {
            'track_number': None,
            'target_address': None,
            'position_polar': (1000.0, 45.0),
            'position_cartesian': None
        })()
        
        self.assertTrue(self.parser.is_valid_track(track))
    
    def test_is_valid_track_invalid(self):
        """Test track validation with no identifying data"""
        track = type('Track', (), {
            'track_number': None,
            'target_address': None,
            'position_polar': None,
            'position_cartesian': None
        })()
        
        self.assertFalse(self.parser.is_valid_track(track))


if __name__ == '__main__':
    unittest.main()
