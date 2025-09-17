"""
Unit tests for detection normalizer
"""

import unittest
import math
from datetime import datetime, timezone

from plugins.dspnor.normalizer import DetectionNormalizer
from plugins.dspnor.schemas import CAT010Track, NMEAData


class TestDetectionNormalizer(unittest.TestCase):
    """Test detection normalizer"""
    
    def setUp(self):
        self.normalizer = DetectionNormalizer(
            conf_map="snr_db:linear:0:30",
            min_conf=0.05,
            max_conf=0.99,
            range_units="m",
            speed_units="mps",
            bearing_is_relative=False
        )
    
    def test_generate_object_id_from_track_number(self):
        """Test object ID generation from track number"""
        track = CAT010Track(track_number=12345)
        object_id = self.normalizer._generate_object_id(track)
        self.assertEqual(object_id, "dspnor_012345")
    
    def test_generate_object_id_from_address(self):
        """Test object ID generation from target address"""
        track = CAT010Track(target_address=0x123456)
        object_id = self.normalizer._generate_object_id(track)
        self.assertEqual(object_id, "dspnor_123456")
    
    def test_generate_object_id_fallback(self):
        """Test object ID generation fallback"""
        track = CAT010Track(time_of_day=3600.0, target_id="TEST", has_mmsi=True)
        object_id = self.normalizer._generate_object_id(track)
        self.assertTrue(object_id.startswith("dspnor_"))
        self.assertEqual(len(object_id), 13)  # "dspnor_" + 6 hex chars
    
    def test_extract_position_polar(self):
        """Test position extraction from polar coordinates"""
        track = CAT010Track(position_polar=(1000.0, 45.0))
        bearing, distance = self.normalizer._extract_position(track, None)
        
        self.assertEqual(bearing, 45.0)
        self.assertEqual(distance, 1000.0)
    
    def test_extract_position_cartesian(self):
        """Test position extraction from cartesian coordinates"""
        track = CAT010Track(position_cartesian=(100.0, 200.0))
        bearing, distance = self.normalizer._extract_position(track, None)
        
        expected_distance = math.sqrt(100*100 + 200*200)
        expected_bearing = math.degrees(math.atan2(100, 200))
        
        self.assertAlmostEqual(distance, expected_distance, places=1)
        self.assertAlmostEqual(bearing, expected_bearing, places=1)
    
    def test_extract_position_with_heading_conversion(self):
        """Test position extraction with heading conversion"""
        track = CAT010Track(position_polar=(1000.0, 45.0))
        current_heading = 30.0
        bearing, distance = self.normalizer._extract_position(track, current_heading)
        
        expected_bearing = (45.0 + 30.0) % 360
        self.assertEqual(bearing, expected_bearing)
        self.assertEqual(distance, 1000.0)
    
    def test_extract_position_relative_mode(self):
        """Test position extraction in relative mode"""
        normalizer = DetectionNormalizer(bearing_is_relative=True)
        track = CAT010Track(position_polar=(1000.0, 45.0))
        current_heading = 30.0
        bearing, distance = normalizer._extract_position(track, current_heading)
        
        # Should not convert in relative mode
        self.assertEqual(bearing, 45.0)
        self.assertEqual(distance, 1000.0)
    
    def test_extract_velocity_polar(self):
        """Test velocity extraction from polar coordinates"""
        track = CAT010Track(velocity_polar=(25.0, 90.0))
        speed, course = self.normalizer._extract_velocity(track)
        
        self.assertEqual(speed, 25.0)
        self.assertEqual(course, 90.0)
    
    def test_extract_velocity_cartesian(self):
        """Test velocity extraction from cartesian coordinates"""
        track = CAT010Track(velocity_cartesian=(20.0, 10.0))
        speed, course = self.normalizer._extract_velocity(track)
        
        expected_speed = math.sqrt(20*20 + 10*10)
        expected_course = math.degrees(math.atan2(20, 10))
        
        self.assertAlmostEqual(speed, expected_speed, places=1)
        self.assertAlmostEqual(course, expected_course, places=1)
    
    def test_extract_velocity_ground_speed(self):
        """Test velocity extraction from ground speed"""
        track = CAT010Track(ground_speed=30.0)
        speed, course = self.normalizer._extract_velocity(track)
        
        self.assertEqual(speed, 30.0)
        self.assertIsNone(course)
    
    def test_calculate_confidence_base(self):
        """Test confidence calculation with base values"""
        track = CAT010Track()
        confidence = self.normalizer._calculate_confidence(track)
        
        self.assertEqual(confidence, 50)  # Base confidence
    
    def test_calculate_confidence_with_quality(self):
        """Test confidence calculation with track quality"""
        track = CAT010Track(track_quality=10)
        confidence = self.normalizer._calculate_confidence(track)
        
        self.assertGreater(confidence, 50)  # Should be boosted
    
    def test_calculate_confidence_with_mmsi(self):
        """Test confidence calculation with MMSI"""
        track = CAT010Track(has_mmsi=True)
        confidence = self.normalizer._calculate_confidence(track)
        
        self.assertEqual(confidence, 70)  # 50 + 20 for MMSI
    
    def test_calculate_confidence_with_target_id(self):
        """Test confidence calculation with target ID"""
        track = CAT010Track(target_id="TEST123")
        confidence = self.normalizer._calculate_confidence(track)
        
        self.assertEqual(confidence, 60)  # 50 + 10 for target ID
    
    def test_calculate_confidence_clamped(self):
        """Test confidence calculation is clamped to valid range"""
        normalizer = DetectionNormalizer(min_conf=0.1, max_conf=0.8)
        track = CAT010Track(track_quality=100)  # Very high quality
        confidence = normalizer._calculate_confidence(track)
        
        self.assertLessEqual(confidence, 80)  # Should be clamped to max_conf * 100
    
    def test_calculate_bearing_error(self):
        """Test bearing error calculation"""
        track = CAT010Track(track_quality=10)
        error = self.normalizer._calculate_bearing_error(track)
        
        self.assertGreater(error, 0)
        self.assertLess(error, 10)  # Should be reasonable
    
    def test_calculate_distance_error(self):
        """Test distance error calculation"""
        track = CAT010Track()
        error = self.normalizer._calculate_distance_error(track, 1000.0)
        
        self.assertGreater(error, 50)  # Minimum error
        self.assertAlmostEqual(error, 100.0, places=0)  # 10% of distance
    
    def test_convert_distance_to_km(self):
        """Test distance conversion to kilometers"""
        normalizer = DetectionNormalizer(range_units="km")
        distance_km = normalizer._convert_distance(1000.0)
        
        self.assertEqual(distance_km, 1.0)
    
    def test_convert_distance_to_meters(self):
        """Test distance conversion to meters"""
        distance_m = self.normalizer._convert_distance(1000.0)
        
        self.assertEqual(distance_m, 1000.0)
    
    def test_convert_speed_to_kts(self):
        """Test speed conversion to knots"""
        normalizer = DetectionNormalizer(speed_units="kts")
        speed_kts = normalizer._convert_speed(10.0)
        
        self.assertAlmostEqual(speed_kts, 19.44, places=1)
    
    def test_convert_speed_to_mps(self):
        """Test speed conversion to m/s"""
        speed_mps = self.normalizer._convert_speed(10.0)
        
        self.assertEqual(speed_mps, 10.0)
    
    def test_get_timestamp_from_time_of_day(self):
        """Test timestamp generation from time of day"""
        track = CAT010Track(time_of_day=3600.0)  # 1 hour
        timestamp = self.normalizer._get_timestamp(track)
        
        self.assertIsInstance(timestamp, datetime)
        self.assertEqual(timestamp.hour, 1)
        self.assertEqual(timestamp.minute, 0)
        self.assertEqual(timestamp.second, 0)
    
    def test_get_timestamp_fallback(self):
        """Test timestamp generation fallback"""
        track = CAT010Track()
        timestamp = self.normalizer._get_timestamp(track)
        
        self.assertIsInstance(timestamp, datetime)
        # Should be recent
        now = datetime.now(timezone.utc)
        diff = abs((now - timestamp).total_seconds())
        self.assertLess(diff, 1.0)
    
    def test_create_raw_data(self):
        """Test raw data creation"""
        track = CAT010Track(
            track_number=12345,
            target_address=0x123456,
            track_quality=10,
            target_id="TEST123",
            has_mmsi=True,
            position_polar=(1000.0, 45.0),
            velocity_polar=(25.0, 90.0)
        )
        
        nmea_data = NMEAData(
            timestamp=datetime.now(timezone.utc),
            heading_deg_true=30.0,
            latitude=40.0,
            longitude=-74.0
        )
        
        raw_data = self.normalizer._create_raw_data(track, nmea_data)
        
        self.assertEqual(raw_data["track_number"], 12345)
        self.assertEqual(raw_data["target_address"], 0x123456)
        self.assertEqual(raw_data["track_quality"], 10)
        self.assertEqual(raw_data["target_id"], "TEST123")
        self.assertTrue(raw_data["has_mmsi"])
        self.assertEqual(raw_data["position_polar"]["range_m"], 1000.0)
        self.assertEqual(raw_data["position_polar"]["bearing_deg"], 45.0)
        self.assertEqual(raw_data["velocity_polar"]["speed_mps"], 25.0)
        self.assertEqual(raw_data["velocity_polar"]["heading_deg"], 90.0)
        self.assertEqual(raw_data["nmea"]["heading_deg_true"], 30.0)
        self.assertEqual(raw_data["nmea"]["latitude"], 40.0)
        self.assertEqual(raw_data["nmea"]["longitude"], -74.0)
    
    def test_parse_conf_map_valid(self):
        """Test confidence mapping parsing"""
        conf_map = self.normalizer._parse_conf_map("snr_db:linear:0:30")
        
        self.assertIsNotNone(conf_map)
        self.assertEqual(conf_map[0], "snr_db")
        self.assertEqual(conf_map[1], "linear")
        self.assertEqual(conf_map[2], 0.0)
        self.assertEqual(conf_map[3], 30.0)
    
    def test_parse_conf_map_invalid(self):
        """Test confidence mapping parsing with invalid input"""
        conf_map = self.normalizer._parse_conf_map("invalid")
        
        self.assertIsNone(conf_map)
    
    def test_normalize_complete_track(self):
        """Test complete track normalization"""
        track = CAT010Track(
            track_number=12345,
            position_polar=(1000.0, 45.0),
            velocity_polar=(25.0, 90.0),
            track_quality=10,
            has_mmsi=True,
            time_of_day=3600.0
        )
        
        detection = self.normalizer.normalize(track, current_heading=30.0)
        
        self.assertIsNotNone(detection)
        self.assertEqual(detection.object_id, "dspnor_012345")
        self.assertEqual(detection.bearing_deg_true, 75.0)  # 45 + 30
        self.assertEqual(detection.distance_m, 1000.0)
        self.assertEqual(detection.speed_mps, 25.0)
        self.assertEqual(detection.course_deg, 90.0)
        self.assertTrue(detection.has_mmsi)
        self.assertGreater(detection.confidence, 50)
        self.assertEqual(detection.track_id, "12345")
    
    def test_normalize_no_position(self):
        """Test normalization with no position data"""
        track = CAT010Track(track_number=12345)
        
        detection = self.normalizer.normalize(track)
        
        self.assertIsNone(detection)


if __name__ == '__main__':
    unittest.main()
