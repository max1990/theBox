"""
Unit Tests for Range Estimation Logic
====================================

Tests for deterministic range estimation with reproducible seeds
and clear hysteresis behavior.
"""

import math
import pytest
from unittest.mock import patch

from plugins.range.range_plugin import RangePlugin


class TestRangeEstimation:
    """Test range estimation logic"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.plugin = RangePlugin()
        
    def test_fixed_mode(self):
        """Test fixed range mode"""
        estimate = self.plugin._fixed_mode()
        
        assert estimate.range_km == self.plugin.fixed_km
        assert estimate.sigma_km == 0.1 * self.plugin.fixed_km
        assert estimate.mode == "FIXED"
        assert "fixed_km" in estimate.details
        
    def test_rf_range_estimation(self):
        """Test RF range estimation"""
        signal = {
            "RSSI": -60.0
        }
        
        range_km, sigma_km = self.plugin._rf_range(signal)
        
        assert range_km is not None
        assert sigma_km is not None
        assert range_km > 0
        assert sigma_km > 0
        assert self.plugin.min_km <= range_km <= self.plugin.max_km
        
    def test_rf_range_bounds(self):
        """Test RF range bounds clamping"""
        # Test minimum bound
        signal = {"RSSI": -100.0}  # Very weak signal
        range_km, sigma_km = self.plugin._rf_range(signal)
        assert range_km >= self.plugin.min_km
        
        # Test maximum bound
        signal = {"RSSI": -20.0}  # Very strong signal
        range_km, sigma_km = self.plugin._rf_range(signal)
        assert range_km <= self.plugin.max_km
        
    def test_rf_range_ewma_smoothing(self):
        """Test RF range EWMA smoothing"""
        signal = {"RSSI": -60.0}
        
        # First estimate
        range1, sigma1 = self.plugin._rf_range(signal)
        
        # Second estimate (should be smoothed)
        range2, sigma2 = self.plugin._rf_range(signal)
        
        # Should be smoothed by EWMA
        assert range2 != range1
        assert abs(range2 - range1) < abs(range1 - self.plugin.fixed_km)
        
    def test_eo_range_estimation(self):
        """Test EO camera range estimation"""
        eo_data = {
            "pixel_height": 50,
            "frame_height": 1080,
            "fov_deg": 54.0
        }
        
        range_km, sigma_km = self.plugin._eo_range(eo_data)
        
        assert range_km is not None
        assert sigma_km is not None
        assert range_km > 0
        assert sigma_km > 0
        assert self.plugin.min_km <= range_km <= self.plugin.max_km
        
    def test_eo_range_bounds(self):
        """Test EO range bounds clamping"""
        # Test minimum bound
        eo_data = {
            "pixel_height": 1000,  # Very large object
            "frame_height": 1080,
            "fov_deg": 54.0
        }
        range_km, sigma_km = self.plugin._eo_range(eo_data)
        assert range_km >= self.plugin.min_km
        
        # Test maximum bound
        eo_data = {
            "pixel_height": 1,  # Very small object
            "frame_height": 1080,
            "fov_deg": 54.0
        }
        range_km, sigma_km = self.plugin._eo_range(eo_data)
        assert range_km <= self.plugin.max_km
        
    def test_eo_range_visibility_effects(self):
        """Test EO range visibility effects"""
        eo_data = {
            "pixel_height": 50,
            "frame_height": 1080,
            "fov_deg": 54.0
        }
        
        # Normal conditions
        range1, sigma1 = self.plugin._eo_range(eo_data)
        
        # Backlit conditions
        eo_data["backlit"] = True
        range2, sigma2 = self.plugin._eo_range(eo_data)
        
        # Poor contrast conditions
        eo_data["backlit"] = False
        eo_data["poor_contrast"] = True
        range3, sigma3 = self.plugin._eo_range(eo_data)
        
        # Sigma should increase with poor visibility
        assert sigma2 > sigma1
        assert sigma3 > sigma1
        
    def test_ir_range_estimation(self):
        """Test IR camera range estimation"""
        ir_data = {
            "pixel_height": 30,
            "frame_height": 1080,
            "fov_deg": 27.0
        }
        
        range_km, sigma_km = self.plugin._ir_range(ir_data)
        
        assert range_km is not None
        assert sigma_km is not None
        assert range_km > 0
        assert sigma_km > 0
        assert self.plugin.min_km <= range_km <= self.plugin.max_km
        
    def test_acoustic_range_estimation(self):
        """Test acoustic range estimation"""
        acoustic_data = {
            "spl_dba": 70.0
        }
        
        range_km, sigma_km = self.plugin._acoustic_range(acoustic_data)
        
        assert range_km is not None
        assert sigma_km is not None
        assert range_km > 0
        assert sigma_km > 0
        assert self.plugin.min_km <= range_km <= self.plugin.max_km
        
    def test_acoustic_range_snr_effects(self):
        """Test acoustic range SNR effects"""
        acoustic_data = {
            "spl_dba": 70.0
        }
        
        # Normal conditions
        range1, sigma1 = self.plugin._acoustic_range(acoustic_data)
        
        # Poor SNR
        acoustic_data["snr_db"] = 5.0
        range2, sigma2 = self.plugin._acoustic_range(acoustic_data)
        
        # Good SNR
        acoustic_data["snr_db"] = 20.0
        range3, sigma3 = self.plugin._acoustic_range(acoustic_data)
        
        # Sigma should increase with poor SNR
        assert sigma2 > sigma1
        assert sigma3 < sigma2
        
    def test_acoustic_range_sea_state_effects(self):
        """Test acoustic range sea state effects"""
        acoustic_data = {
            "spl_dba": 70.0
        }
        
        # Calm seas
        acoustic_data["sea_state"] = 1
        range1, sigma1 = self.plugin._acoustic_range(acoustic_data)
        
        # Rough seas
        acoustic_data["sea_state"] = 5
        range2, sigma2 = self.plugin._acoustic_range(acoustic_data)
        
        # Sigma should increase with rough seas
        assert sigma2 > sigma1
        
    def test_cue_fusion(self):
        """Test multiple cue fusion"""
        signal = {"RSSI": -60.0}
        eo = {
            "pixel_height": 50,
            "frame_height": 1080,
            "fov_deg": 54.0
        }
        
        estimate = self.plugin.estimate_km(signal=signal, eo=eo)
        
        assert estimate.mode == "HYBRID"
        assert estimate.range_km is not None
        assert estimate.sigma_km is not None
        assert "rf" in estimate.details
        assert "eo" in estimate.details
        assert "fused" in estimate.details
        
    def test_single_cue_mode(self):
        """Test single cue mode"""
        signal = {"RSSI": -60.0}
        
        estimate = self.plugin.estimate_km(signal=signal)
        
        assert estimate.mode == "rf"
        assert estimate.range_km is not None
        assert estimate.sigma_km is not None
        assert "rf" in estimate.details
        
    def test_no_cues_fallback(self):
        """Test fallback when no cues available"""
        estimate = self.plugin.estimate_km()
        
        assert estimate.mode == "FIXED"
        assert estimate.range_km == self.plugin.fixed_km
        
    def test_invalid_input_handling(self):
        """Test handling of invalid inputs"""
        # Test with None values
        estimate = self.plugin.estimate_km(signal=None, eo=None)
        assert estimate.mode == "FIXED"
        
        # Test with invalid signal data
        signal = {"RSSI": "invalid"}
        estimate = self.plugin.estimate_km(signal=signal)
        assert estimate.mode == "FIXED"
        
        # Test with missing required fields
        eo = {"pixel_height": 50}  # Missing frame_height
        estimate = self.plugin.estimate_km(eo=eo)
        assert estimate.mode == "FIXED"
        
    def test_deterministic_behavior(self):
        """Test that results are deterministic"""
        signal = {"RSSI": -60.0}
        eo = {
            "pixel_height": 50,
            "frame_height": 1080,
            "fov_deg": 54.0
        }
        
        # Run multiple times with same inputs
        estimate1 = self.plugin.estimate_km(signal=signal, eo=eo)
        estimate2 = self.plugin.estimate_km(signal=signal, eo=eo)
        
        assert abs(estimate1.range_km - estimate2.range_km) < 1e-10
        assert abs(estimate1.sigma_km - estimate2.sigma_km) < 1e-10
        
    def test_range_constraints_validation(self):
        """Test range constraints validation"""
        # Test valid constraints
        self.plugin.min_km = 0.1
        self.plugin.max_km = 8.0
        self.plugin.fixed_km = 2.0
        
        # Should not raise exception
        self.plugin._validate_range_constraints()
        
        # Test invalid constraints
        self.plugin.min_km = 5.0
        self.plugin.max_km = 3.0
        
        with pytest.raises(ValueError):
            self.plugin._validate_range_constraints()
            
        # Test fixed range out of bounds
        self.plugin.min_km = 0.1
        self.plugin.max_km = 8.0
        self.plugin.fixed_km = 10.0
        
        with pytest.raises(ValueError):
            self.plugin._validate_range_constraints()
            
    def test_ewma_state_management(self):
        """Test EWMA state management"""
        signal = {"RSSI": -60.0}
        
        # First call should initialize state
        range1, sigma1 = self.plugin._rf_range(signal)
        assert "rf_default" in self.plugin.ewma_state
        
        # Second call should use existing state
        range2, sigma2 = self.plugin._rf_range(signal)
        assert range2 != range1  # Should be smoothed
        
        # State should be updated
        assert self.plugin.ewma_state["rf_default"] == range2
        
    def test_sigma_clamping(self):
        """Test sigma clamping"""
        # Test minimum sigma
        signal = {"RSSI": -60.0}
        range_km, sigma_km = self.plugin._rf_range(signal)
        
        min_sigma = 0.05 * range_km
        max_sigma = 1.0 * range_km
        
        assert min_sigma <= sigma_km <= max_sigma
        
    def test_fusion_weights(self):
        """Test fusion weights calculation"""
        cues = {
            "rf": (1.0, 0.1),
            "eo": (2.0, 0.2)
        }
        
        estimate = self.plugin._fuse_cues(cues)
        
        # Fused range should be between individual ranges
        assert min(1.0, 2.0) <= estimate.range_km <= max(1.0, 2.0)
        
        # Fused sigma should be less than individual sigmas
        assert estimate.sigma_km < 0.1
        assert estimate.sigma_km < 0.2
        
    def test_edge_cases(self):
        """Test edge cases"""
        # Test with zero pixel height
        eo = {
            "pixel_height": 0,
            "frame_height": 1080,
            "fov_deg": 54.0
        }
        range_km, sigma_km = self.plugin._eo_range(eo)
        assert range_km is None
        assert sigma_km is None
        
        # Test with negative values
        signal = {"RSSI": -200.0}  # Extremely weak signal
        range_km, sigma_km = self.plugin._rf_range(signal)
        assert range_km is not None  # Should be clamped to min
        
        # Test with very large values
        signal = {"RSSI": 100.0}  # Extremely strong signal
        range_km, sigma_km = self.plugin._rf_range(signal)
        assert range_km is not None  # Should be clamped to max


class TestRangeEstimationIntegration:
    """Integration tests for range estimation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.plugin = RangePlugin()
        
    def test_full_estimation_workflow(self):
        """Test complete estimation workflow"""
        # Test with multiple cues
        signal = {"RSSI": -60.0}
        eo = {
            "pixel_height": 50,
            "frame_height": 1080,
            "fov_deg": 54.0
        }
        ir = {
            "pixel_height": 30,
            "frame_height": 1080,
            "fov_deg": 27.0
        }
        acoustic = {
            "spl_dba": 70.0,
            "snr_db": 15.0,
            "sea_state": 2
        }
        
        estimate = self.plugin.estimate_km(
            signal=signal,
            eo=eo,
            ir=ir,
            ac=acoustic
        )
        
        assert estimate.mode == "HYBRID"
        assert estimate.range_km is not None
        assert estimate.sigma_km is not None
        assert len(estimate.details) >= 4  # rf, eo, ir, acoustic, fused
        
    def test_mode_switching(self):
        """Test mode switching"""
        # Test fixed mode
        self.plugin.mode = "fixed"
        estimate = self.plugin.estimate_km()
        assert estimate.mode == "FIXED"
        
        # Test RF mode
        self.plugin.mode = "rf"
        signal = {"RSSI": -60.0}
        estimate = self.plugin.estimate_km(signal=signal)
        assert estimate.mode == "rf"
        
        # Test hybrid mode
        self.plugin.mode = "hybrid"
        signal = {"RSSI": -60.0}
        eo = {
            "pixel_height": 50,
            "frame_height": 1080,
            "fov_deg": 54.0
        }
        estimate = self.plugin.estimate_km(signal=signal, eo=eo)
        assert estimate.mode == "HYBRID"
        
    def test_estimation_counting(self):
        """Test estimation counting"""
        initial_count = self.plugin.estimates
        
        # Make some estimations
        self.plugin.estimate_km(signal={"RSSI": -60.0})
        self.plugin.estimate_km(eo={"pixel_height": 50, "frame_height": 1080})
        
        assert self.plugin.estimates == initial_count + 2
        
    def test_reproducible_seeds(self):
        """Test that results are reproducible with same random seeds"""
        import random
        
        # Set random seed
        random.seed(42)
        
        signal = {"RSSI": -60.0}
        eo = {
            "pixel_height": 50,
            "frame_height": 1080,
            "fov_deg": 54.0
        }
        
        # Run multiple times with same seed
        estimate1 = self.plugin.estimate_km(signal=signal, eo=eo)
        
        random.seed(42)
        estimate2 = self.plugin.estimate_km(signal=signal, eo=eo)
        
        assert abs(estimate1.range_km - estimate2.range_km) < 1e-10
        assert abs(estimate1.sigma_km - estimate2.sigma_km) < 1e-10
