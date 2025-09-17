"""
Integration tests for schema validation
"""

import unittest
from datetime import datetime, timezone

from plugins.dspnor.schemas import NormalizedDetection


class TestContractSchema(unittest.TestCase):
    """Test normalized detection schema contract"""

    def test_minimal_detection_schema(self):
        """Test minimal detection schema validation"""
        detection = NormalizedDetection(
            object_id="dspnor_123456",
            time_utc=datetime.now(timezone.utc),
            bearing_deg_true=45.0,
            bearing_error_deg=5.0,
            distance_m=1000.0,
            distance_error_m=100.0,
            altitude_m=0.0,
            altitude_error_m=20.0,
            speed_mps=25.0,
            course_deg=90.0,
            confidence=80,
            track_id="123456",
            has_mmsi=True,
            raw_data={"test": "data"},
        )

        # Should serialize to JSON without error
        json_str = detection.json()
        self.assertIsInstance(json_str, str)

        # Should deserialize from JSON
        parsed = NormalizedDetection.parse_raw(json_str)
        self.assertEqual(parsed.object_id, "dspnor_123456")
        self.assertEqual(parsed.bearing_deg_true, 45.0)
        self.assertEqual(parsed.confidence, 80)

    def test_detection_with_optional_fields(self):
        """Test detection with optional fields"""
        detection = NormalizedDetection(
            object_id="dspnor_789012",
            time_utc=datetime.now(timezone.utc),
            bearing_deg_true=180.0,
            bearing_error_deg=2.0,
            confidence=95,
        )

        # Optional fields should have defaults
        self.assertIsNone(detection.distance_m)
        self.assertIsNone(detection.distance_error_m)
        self.assertEqual(detection.altitude_m, 0.0)
        self.assertEqual(detection.altitude_error_m, 20.0)
        self.assertIsNone(detection.speed_mps)
        self.assertIsNone(detection.course_deg)
        self.assertIsNone(detection.track_id)
        self.assertFalse(detection.has_mmsi)
        self.assertEqual(detection.raw_data, {})

    def test_confidence_validation(self):
        """Test confidence value validation"""
        # Valid confidence values
        for conf in [0, 50, 100]:
            detection = NormalizedDetection(
                object_id="test",
                time_utc=datetime.now(timezone.utc),
                bearing_deg_true=0.0,
                confidence=conf,
            )
            self.assertEqual(detection.confidence, conf)

        # Invalid confidence values should be clamped
        detection = NormalizedDetection(
            object_id="test",
            time_utc=datetime.now(timezone.utc),
            bearing_deg_true=0.0,
            confidence=150,  # Too high
        )
        self.assertEqual(detection.confidence, 100)

        detection = NormalizedDetection(
            object_id="test",
            time_utc=datetime.now(timezone.utc),
            bearing_deg_true=0.0,
            confidence=-10,  # Too low
        )
        self.assertEqual(detection.confidence, 0)

    def test_json_schema_generation(self):
        """Test JSON schema generation"""
        schema = NormalizedDetection.schema()

        self.assertIn("properties", schema)
        self.assertIn("object_id", schema["properties"])
        self.assertIn("time_utc", schema["properties"])
        self.assertIn("bearing_deg_true", schema["properties"])
        self.assertIn("confidence", schema["properties"])

        # Check required fields
        self.assertIn("object_id", schema["required"])
        self.assertIn("time_utc", schema["required"])
        self.assertIn("bearing_deg_true", schema["required"])

    def test_serialization_roundtrip(self):
        """Test serialization and deserialization roundtrip"""
        original = NormalizedDetection(
            object_id="dspnor_roundtrip",
            time_utc=datetime.now(timezone.utc),
            bearing_deg_true=270.0,
            bearing_error_deg=3.0,
            distance_m=500.0,
            distance_error_m=50.0,
            altitude_m=100.0,
            altitude_error_m=10.0,
            speed_mps=15.0,
            course_deg=275.0,
            confidence=85,
            track_id="roundtrip",
            has_mmsi=False,
            raw_data={"test": "roundtrip", "value": 42},
        )

        # Serialize to dict
        data = original.dict()

        # Deserialize from dict
        restored = NormalizedDetection(**data)

        # Should be equal
        self.assertEqual(original.object_id, restored.object_id)
        self.assertEqual(original.bearing_deg_true, restored.bearing_deg_true)
        self.assertEqual(original.distance_m, restored.distance_m)
        self.assertEqual(original.confidence, restored.confidence)
        self.assertEqual(original.raw_data, restored.raw_data)

    def test_iso_timestamp_format(self):
        """Test ISO timestamp format"""
        now = datetime.now(timezone.utc)
        detection = NormalizedDetection(
            object_id="test", time_utc=now, bearing_deg_true=0.0
        )

        # Should serialize to ISO format
        data = detection.dict()
        self.assertIsInstance(data["time_utc"], str)
        self.assertTrue(data["time_utc"].endswith("Z"))

        # Should deserialize from ISO format
        restored = NormalizedDetection(**data)
        self.assertEqual(restored.time_utc, now)


if __name__ == "__main__":
    unittest.main()
