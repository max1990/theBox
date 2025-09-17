"""
Test suite for Vision Plugin Logic
Tests the 8 Vision scenarios with deterministic mocks
"""

from unittest.mock import patch

import numpy as np
import pytest

from plugins.vision.vision_plugin import Detection, Track, VisionPlugin


class TestVisionLogic:
    """Test cases for VisionPlugin logic"""

    def setup_method(self):
        """Set up test environment"""
        # Mock environment variables
        import os

        os.environ.update(
            {
                "VISION_BACKEND": "cpu",
                "VISION_MODEL_PATH": "",
                "VISION_INPUT_RES": "640",
                "VISION_ROI_HALF_DEG": "15",
                "VISION_FRAME_SKIP": "2",
                "VISION_N_CONSEC_FOR_TRUE": "3",
                "VISION_LATENCY_MS": "5000",
                "VISION_MAX_DWELL_MS": "7000",
                "VISION_SWEEP_STEP_DEG": "12",
                "VISION_PRIORITY": "rf_power",
                "VISION_VERDICT_DEFAULT": "true",
                "VISION_LABEL_DEFAULT": "Object",
                "CAPTURE_API": "opencv",
                "CAPTURE_RES": "1920x1080@30",
                "BOW_ZERO_DEG": "0.0",
                "VISION_BEARING_OFFSET_DEG": "0.0",
                "EO_FOV_WIDE_DEG": "54.0",
                "EO_FOV_NARROW_DEG": "2.0",
                "IR_FOV_WIDE_DEG": "27.0",
                "IR_FOV_NARROW_DEG": "1.3",
            }
        )
        self.plugin = VisionPlugin()

    @pytest.mark.asyncio
    async def test_missing_model_fallback(self):
        """Test fallback when model is missing"""
        # Model should not be loaded (empty path)
        assert not self.plugin.model_loaded

        result = await self.plugin.run_verification("test_track", 45.0, 1000)

        assert result.verified is True  # Default verdict
        assert result.label == "Object"
        assert result.latency_ms == 5000

    @pytest.mark.asyncio
    async def test_latency_cap_exceeded(self):
        """Test latency cap enforcement"""
        # Set last capture time far in the past
        self.plugin.last_capture_time = 0

        result = await self.plugin.run_verification("test_track", 45.0, 10000)

        assert result.verified is True  # Default verdict
        assert result.latency_ms > 5000

    @pytest.mark.asyncio
    async def test_dwell_timeout_sweep_signal(self):
        """Test dwell timeout triggers sweep signal"""
        # Set dwell start time far in the past
        self.plugin.dwell_start_time = 0

        result = await self.plugin.run_verification("test_track", 45.0, 8000)

        assert result.verified is False
        assert result.label == "sweep_needed"
        assert "sweep_step_deg" in result.tracker

    @pytest.mark.asyncio
    async def test_frame_skip_logic(self):
        """Test frame skip logic"""
        # First frame (should be processed)
        self.plugin.frame_count = 0
        result1 = await self.plugin.run_verification("test_track", 45.0, 1000)

        # Second frame (should be skipped)
        self.plugin.frame_count = 1
        result2 = await self.plugin.run_verification("test_track", 45.0, 1000)

        # Third frame (should be skipped)
        self.plugin.frame_count = 2
        result3 = await self.plugin.run_verification("test_track", 45.0, 1000)

        # Fourth frame (should be processed)
        self.plugin.frame_count = 3
        result4 = await self.plugin.run_verification("test_track", 45.0, 1000)

        # Only frames 0 and 3 should be processed (every 3rd frame)
        assert result2.label == "frame_skipped"
        assert result3.label == "frame_skipped"

    @pytest.mark.asyncio
    async def test_roi_computation(self):
        """Test ROI bounds computation"""
        # Test with different bearings
        test_cases = [
            (0.0, (0, 0, 480, 1080)),  # North
            (90.0, (480, 0, 960, 1080)),  # East
            (180.0, (960, 0, 1440, 1080)),  # South
            (270.0, (1440, 0, 1920, 1080)),  # West
        ]

        for bearing, expected_bounds in test_cases:
            self.plugin.current_bearing = bearing
            bounds = self.plugin._compute_roi_bounds()

            # Check that bounds are reasonable
            assert bounds[0] >= 0
            assert bounds[2] <= 1920
            assert bounds[1] == 0
            assert bounds[3] == 1080

    def test_detection_parsing(self):
        """Test YOLO output parsing"""
        # Mock YOLO output
        mock_output = np.zeros((1, 84, 8400))

        # Set up a detection at index 100
        mock_output[0, 0, 100] = 0.5  # x_center
        mock_output[0, 1, 100] = 0.5  # y_center
        mock_output[0, 2, 100] = 0.1  # width
        mock_output[0, 3, 100] = 0.1  # height
        mock_output[0, 4, 100] = 0.8  # confidence for class 0

        detections = self.plugin._parse_yolo_outputs(mock_output, (0, 0, 100, 100))

        assert len(detections) == 1
        assert detections[0].confidence == 0.8
        assert detections[0].class_id == 0
        assert detections[0].class_name == "Object"

    def test_tracking_iou_calculation(self):
        """Test IoU calculation for tracking"""
        bbox1 = (0.0, 0.0, 1.0, 1.0)  # Unit square
        bbox2 = (0.5, 0.5, 1.5, 1.5)  # Overlapping square

        iou = self.plugin._compute_iou(bbox1, bbox2)

        # Expected IoU = intersection / union
        # intersection = 0.5 * 0.5 = 0.25
        # union = 1.0 + 1.0 - 0.25 = 1.75
        # IoU = 0.25 / 1.75 ≈ 0.143
        expected_iou = 0.25 / 1.75
        assert abs(iou - expected_iou) < 0.001

    def test_tracking_update(self):
        """Test tracking update logic"""
        # Create mock detections
        detection1 = Detection(
            bbox=(0.1, 0.1, 0.3, 0.3), confidence=0.8, class_id=0, class_name="Object"
        )

        detection2 = Detection(
            bbox=(0.15, 0.15, 0.35, 0.35),  # Overlapping
            confidence=0.9,
            class_id=0,
            class_name="Object",
        )

        # First detection should create new track
        self.plugin._update_tracking([detection1], 1.0)
        assert len(self.plugin.tracks) == 1

        track_id = list(self.plugin.tracks.keys())[0]
        track = self.plugin.tracks[track_id]
        assert track.consecutive_detections == 1

        # Second detection should update existing track
        self.plugin._update_tracking([detection2], 2.0)
        assert len(self.plugin.tracks) == 1
        assert track.consecutive_detections == 2

    def test_verification_criteria(self):
        """Test verification criteria (N consecutive detections)"""
        # Create track with insufficient consecutive detections
        track1 = Track(
            track_id=1,
            bbox=(0.1, 0.1, 0.3, 0.3),
            confidence=0.8,
            class_name="Object",
            last_seen=1.0,
            consecutive_detections=2,  # Less than required 3
            age=1,
        )
        self.plugin.tracks[1] = track1

        # Should not be verified
        verified_track = self.plugin._check_verification("test_track")
        assert verified_track is None

        # Add more consecutive detections
        track1.consecutive_detections = 3

        # Should now be verified
        verified_track = self.plugin._check_verification("test_track")
        assert verified_track is not None
        assert verified_track.track_id == 1

    def test_track_cleanup(self):
        """Test old track cleanup"""
        # Create old track
        old_track = Track(
            track_id=1,
            bbox=(0.1, 0.1, 0.3, 0.3),
            confidence=0.8,
            class_name="Object",
            last_seen=1.0,  # Old timestamp
            consecutive_detections=1,
            age=1,
        )
        self.plugin.tracks[1] = old_track

        # Update tracking with current time
        self.plugin._update_tracking([], 35.0)  # 34 seconds later

        # Old track should be removed
        assert 1 not in self.plugin.tracks

    @pytest.mark.asyncio
    async def test_bearing_offset_application(self):
        """Test bearing offset application"""
        # Set offsets
        self.plugin.bow_zero_deg = 10.0
        self.plugin.bearing_offset_deg = 5.0

        result = await self.plugin.run_verification("test_track", 45.0, 1000)

        # Bearing should be adjusted: 45 + 10 + 5 = 60
        assert self.plugin.current_bearing == 60.0

    @pytest.mark.asyncio
    async def test_capture_failure_handling(self):
        """Test handling of capture failures"""
        # Mock capture to return None
        with patch.object(self.plugin, "_capture_frame", return_value=None):
            result = await self.plugin.run_verification("test_track", 45.0, 1000)

            assert result.verified is False
            assert result.label == "capture_failed"

    def test_roi_sector_computation(self):
        """Test ROI sector computation with different FOVs"""
        from mvp.geometry import compute_roi_sector

        # Test with wide FOV
        start, end = compute_roi_sector(90.0, 54.0, 15.0)
        assert start < 90.0
        assert end > 90.0
        assert end - start == 30.0  # 2 * 15 degrees

        # Test with narrow FOV
        start, end = compute_roi_sector(90.0, 2.0, 15.0)
        assert start < 90.0
        assert end > 90.0
        # Should use FOV/4 as half-width when FOV is smaller than ROI
        assert end - start == 0.5  # 2.0 / 4

    @pytest.mark.asyncio
    async def test_vision_scenario_1(self):
        """Test scenario 1: Model missing -> Default verdict"""
        # Model already not loaded (empty path)
        result = await self.plugin.run_verification("track1", 45.0, 1000)

        assert result.verified is True
        assert result.label == "Object"
        assert result.latency_ms == 5000

    @pytest.mark.asyncio
    async def test_vision_scenario_2(self):
        """Test scenario 2: Latency exceeded -> Default verdict"""
        self.plugin.last_capture_time = 0
        result = await self.plugin.run_verification("track2", 45.0, 10000)

        assert result.verified is True
        assert result.latency_ms > 5000

    @pytest.mark.asyncio
    async def test_vision_scenario_3(self):
        """Test scenario 3: Dwell timeout -> Sweep signal"""
        self.plugin.dwell_start_time = 0
        result = await self.plugin.run_verification("track3", 45.0, 8000)

        assert result.verified is False
        assert result.label == "sweep_needed"
        assert result.tracker["sweep_step_deg"] == 12

    @pytest.mark.asyncio
    async def test_vision_scenario_4(self):
        """Test scenario 4: Frame skip -> Skip processing"""
        self.plugin.frame_count = 1  # Should be skipped
        result = await self.plugin.run_verification("track4", 45.0, 1000)

        assert result.verified is False
        assert result.label == "frame_skipped"

    @pytest.mark.asyncio
    async def test_vision_scenario_5(self):
        """Test scenario 5: No detections -> Not verified"""
        # Mock empty detections
        with patch.object(self.plugin, "_run_detection", return_value=[]):
            result = await self.plugin.run_verification("track5", 45.0, 1000)

            assert result.verified is False
            assert result.label == "not_verified"

    @pytest.mark.asyncio
    async def test_vision_scenario_6(self):
        """Test scenario 6: Insufficient consecutive detections -> Not verified"""
        # Create track with insufficient detections
        track = Track(
            track_id=1,
            bbox=(0.1, 0.1, 0.3, 0.3),
            confidence=0.8,
            class_name="Object",
            last_seen=1.0,
            consecutive_detections=2,  # Less than required 3
            age=1,
        )
        self.plugin.tracks[1] = track

        # Mock detection that updates tracking
        detection = Detection(
            bbox=(0.1, 0.1, 0.3, 0.3), confidence=0.8, class_id=0, class_name="Object"
        )

        with patch.object(self.plugin, "_run_detection", return_value=[detection]):
            result = await self.plugin.run_verification("track6", 45.0, 1000)

            assert result.verified is False
            assert result.label == "not_verified"

    @pytest.mark.asyncio
    async def test_vision_scenario_7(self):
        """Test scenario 7: Sufficient consecutive detections -> Verified"""
        # Create track with sufficient detections
        track = Track(
            track_id=1,
            bbox=(0.1, 0.1, 0.3, 0.3),
            confidence=0.8,
            class_name="Drone",
            last_seen=1.0,
            consecutive_detections=3,  # Meets requirement
            age=1,
        )
        self.plugin.tracks[1] = track

        # Mock detection that updates tracking
        detection = Detection(
            bbox=(0.1, 0.1, 0.3, 0.3), confidence=0.8, class_id=0, class_name="Drone"
        )

        with patch.object(self.plugin, "_run_detection", return_value=[detection]):
            result = await self.plugin.run_verification("track7", 45.0, 1000)

            assert result.verified is True
            assert result.label == "Drone"
            assert result.bbox == (0.1, 0.1, 0.3, 0.3)
            assert result.tracker["track_id"] == 1
            assert result.tracker["consecutive_detections"] == 4  # Incremented

    @pytest.mark.asyncio
    async def test_vision_scenario_8(self):
        """Test scenario 8: Multiple tracks, only one verified"""
        # Create multiple tracks
        track1 = Track(1, (0.1, 0.1, 0.3, 0.3), 0.8, "Object", 1.0, 2, 1)  # Not enough
        track2 = Track(2, (0.4, 0.4, 0.6, 0.6), 0.9, "Drone", 1.0, 3, 1)  # Enough
        track3 = Track(3, (0.7, 0.7, 0.9, 0.9), 0.7, "Object", 1.0, 1, 1)  # Not enough

        self.plugin.tracks = {1: track1, 2: track2, 3: track3}

        # Mock detection
        detection = Detection(
            bbox=(0.4, 0.4, 0.6, 0.6), confidence=0.9, class_id=0, class_name="Drone"
        )

        with patch.object(self.plugin, "_run_detection", return_value=[detection]):
            result = await self.plugin.run_verification("track8", 45.0, 1000)

            assert result.verified is True
            assert result.label == "Drone"
            assert result.tracker["track_id"] == 2
