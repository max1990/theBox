"""
Test suite for Range Plugin
Tests the 12-row Range Test Matrix with specified tolerances
"""

from plugins.range.range_plugin import RangePlugin


class TestRangePlugin:
    """Test cases for RangePlugin"""

    def setup_method(self):
        """Set up test environment"""
        # Mock environment variables
        import os

        os.environ.update(
            {
                "RANGE_MODE": "hybrid",
                "RANGE_FIXED_KM": "2.0",
                "RANGE_RSSI_REF_DBM": "-50.0",
                "RANGE_RSSI_REF_KM": "2.0",
                "RANGE_MIN_KM": "0.1",
                "RANGE_MAX_KM": "8.0",
                "RANGE_EWMA_ALPHA": "0.4",
                "EO_FOV_WIDE_DEG": "54.0",
                "EO_FOV_NARROW_DEG": "2.0",
                "IR_FOV_WIDE_DEG": "27.0",
                "IR_FOV_NARROW_DEG": "1.3",
            }
        )
        self.plugin = RangePlugin()

    def test_fixed_mode(self):
        """Test fixed range mode"""
        # Set fixed mode
        import os

        os.environ["RANGE_MODE"] = "fixed"
        plugin = RangePlugin()

        result = plugin.estimate_km()
        assert result.mode == "FIXED"
        assert result.range_km == 2.0
        assert result.sigma_km == 0.2  # 0.1 * 2.0
        assert "fixed_km" in result.details

    def test_rf_only_rssi(self):
        """Test RF-only range estimation with RSSI"""
        import os

        os.environ["RANGE_MODE"] = "rssi"
        plugin = RangePlugin()

        # Test cases from Range Test Matrix
        test_cases = [
            # (RSSI_dbm, expected_range_km, tolerance_km)
            (-30, 0.1, 0.02),  # Strong signal -> close range
            (-50, 2.0, 0.02),  # Reference signal
            (-70, 8.0, 0.05),  # Weak signal -> far range
            (-90, 8.0, 0.05),  # Very weak signal -> clamped to max
        ]

        for rssi, expected, tolerance in test_cases:
            signal = {"RSSI": rssi}
            result = plugin.estimate_km(signal=signal)

            assert result.mode == "rf"
            assert abs(result.range_km - expected) <= tolerance
            assert result.sigma_km > 0
            assert "rf" in result.details

    def test_eo_camera_range(self):
        """Test EO camera range estimation"""
        import os

        os.environ["RANGE_MODE"] = "hybrid"
        plugin = RangePlugin()

        # Test cases for EO camera
        test_cases = [
            # (pixel_height, frame_height, fov_deg, expected_range_km, tolerance_km)
            (50, 1080, 54.0, 0.5, 0.02),  # Large object -> close
            (10, 1080, 54.0, 2.5, 0.05),  # Medium object -> medium range
            (5, 1080, 54.0, 5.0, 0.05),  # Small object -> far
        ]

        for pixel_h, frame_h, fov, expected, tolerance in test_cases:
            eo_data = {"pixel_height": pixel_h, "frame_height": frame_h, "fov_deg": fov}
            result = plugin.estimate_km(eo=eo_data)

            assert result.mode == "eo"
            assert abs(result.range_km - expected) <= tolerance
            assert result.sigma_km > 0
            assert "eo" in result.details

    def test_ir_camera_range(self):
        """Test IR camera range estimation"""
        import os

        os.environ["RANGE_MODE"] = "hybrid"
        plugin = RangePlugin()

        # Test cases for IR camera
        test_cases = [
            # (pixel_height, frame_height, fov_deg, expected_range_km, tolerance_km)
            (30, 1080, 27.0, 0.5, 0.02),  # Large object -> close
            (6, 1080, 27.0, 2.5, 0.05),  # Medium object -> medium range
            (3, 1080, 27.0, 5.0, 0.05),  # Small object -> far
        ]

        for pixel_h, frame_h, fov, expected, tolerance in test_cases:
            ir_data = {"pixel_height": pixel_h, "frame_height": frame_h, "fov_deg": fov}
            result = plugin.estimate_km(ir=ir_data)

            assert result.mode == "ir"
            assert abs(result.range_km - expected) <= tolerance
            assert result.sigma_km > 0
            assert "ir" in result.details

    def test_acoustic_range(self):
        """Test acoustic range estimation"""
        import os

        os.environ["RANGE_MODE"] = "hybrid"
        plugin = RangePlugin()

        # Test cases for acoustic
        test_cases = [
            # (spl_dba, expected_range_km, tolerance_km)
            (100, 0.1, 0.02),  # Very loud -> close
            (80, 1.0, 0.02),  # Reference level
            (60, 10.0, 0.05),  # Quiet -> far (but clamped)
            (40, 100.0, 0.05),  # Very quiet -> very far (but clamped)
        ]

        for spl, expected, tolerance in test_cases:
            ac_data = {"spl_dba": spl}
            result = plugin.estimate_km(ac=ac_data)

            assert result.mode == "acoustic"
            # Clamp expected to bounds
            expected = max(0.1, min(8.0, expected))
            assert abs(result.range_km - expected) <= tolerance
            assert result.sigma_km > 0
            assert "acoustic" in result.details

    def test_hybrid_fusion(self):
        """Test hybrid fusion of multiple cues"""
        import os

        os.environ["RANGE_MODE"] = "hybrid"
        plugin = RangePlugin()

        # Test with multiple cues
        signal = {"RSSI": -50}
        eo_data = {"pixel_height": 20, "frame_height": 1080, "fov_deg": 54.0}

        result = plugin.estimate_km(signal=signal, eo=eo_data)

        assert result.mode == "HYBRID"
        assert result.range_km is not None
        assert result.sigma_km is not None
        assert "rf" in result.details
        assert "eo" in result.details
        assert "fused" in result.details

    def test_ewma_smoothing(self):
        """Test EWMA smoothing for RF range"""
        import os

        os.environ["RANGE_MODE"] = "rssi"
        plugin = RangePlugin()

        # First estimate
        signal1 = {"RSSI": -50}
        result1 = plugin.estimate_km(signal=signal1)

        # Second estimate with same RSSI
        signal2 = {"RSSI": -50}
        result2 = plugin.estimate_km(signal=signal2)

        # Results should be the same (no smoothing on first call)
        assert abs(result1.range_km - result2.range_km) < 0.001

    def test_range_bounds(self):
        """Test range clamping to min/max bounds"""
        import os

        os.environ["RANGE_MODE"] = "rssi"
        plugin = RangePlugin()

        # Very strong signal (should clamp to min)
        signal_strong = {"RSSI": -10}
        result_strong = plugin.estimate_km(signal=signal_strong)
        assert result_strong.range_km >= 0.1

        # Very weak signal (should clamp to max)
        signal_weak = {"RSSI": -120}
        result_weak = plugin.estimate_km(signal=signal_weak)
        assert result_weak.range_km <= 8.0

    def test_uncertainty_bounds(self):
        """Test uncertainty bounds"""
        import os

        os.environ["RANGE_MODE"] = "rssi"
        plugin = RangePlugin()

        signal = {"RSSI": -50}
        result = plugin.estimate_km(signal=signal)

        # Uncertainty should be within bounds
        range_km = result.range_km
        sigma_km = result.sigma_km

        assert sigma_km >= 0.05 * range_km  # Min uncertainty
        assert sigma_km <= 1.0 * range_km  # Max uncertainty

    def test_backlit_uncertainty(self):
        """Test increased uncertainty for backlit conditions"""
        import os

        os.environ["RANGE_MODE"] = "hybrid"
        plugin = RangePlugin()

        # Normal EO data
        eo_normal = {"pixel_height": 20, "frame_height": 1080, "fov_deg": 54.0}
        result_normal = plugin.estimate_km(eo=eo_normal)

        # Backlit EO data
        eo_backlit = {
            "pixel_height": 20,
            "frame_height": 1080,
            "fov_deg": 54.0,
            "backlit": True,
        }
        result_backlit = plugin.estimate_km(eo=eo_backlit)

        # Backlit should have higher uncertainty
        assert result_backlit.sigma_km > result_normal.sigma_km

    def test_sea_state_uncertainty(self):
        """Test increased uncertainty for rough sea state"""
        import os

        os.environ["RANGE_MODE"] = "hybrid"
        plugin = RangePlugin()

        # Normal acoustic data
        ac_normal = {"spl_dba": 80}
        result_normal = plugin.estimate_km(ac=ac_normal)

        # Rough sea state acoustic data
        ac_rough = {"spl_dba": 80, "sea_state": 5}
        result_rough = plugin.estimate_km(ac=ac_rough)

        # Rough seas should have higher uncertainty
        assert result_rough.sigma_km > result_normal.sigma_km

    def test_no_cues_fallback(self):
        """Test fallback to fixed mode when no cues available"""
        import os

        os.environ["RANGE_MODE"] = "hybrid"
        plugin = RangePlugin()

        # No cues provided
        result = plugin.estimate_km()

        assert result.mode == "FIXED"
        assert result.range_km == 2.0
        assert result.sigma_km == 0.2
