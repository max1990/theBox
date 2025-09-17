"""
Unit Tests for Confidence Fusion Logic
=====================================

Tests for deterministic confidence fusion with reproducible seeds
and clear hysteresis behavior.
"""

import math
import pytest
from unittest.mock import patch

from plugins.confidence.confidence_plugin import ConfidencePlugin


class TestConfidenceFusion:
    """Test confidence fusion logic"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.plugin = ConfidencePlugin()
        
    def test_initial_score(self):
        """Test initial confidence score"""
        score = self.plugin.initial_score()
        assert score == self.plugin.base
        assert 0 <= score <= 1
        
    def test_bayesian_update_basic(self):
        """Test basic Bayesian update"""
        # Test with simple cues
        cues = {
            "track_id": "test_track",
            "rf": 0.8,
            "vision": 0.9
        }
        
        update = self.plugin.update(0.5, cues)
        
        assert 0 <= update.confidence_0_1 <= 1
        assert update.reason == "bayesian_update"
        assert "log_odds_delta" in update.details
        assert "cues" in update.details
        
    def test_bayesian_update_deterministic(self):
        """Test that Bayesian update is deterministic with same inputs"""
        cues = {
            "track_id": "test_track",
            "rf": 0.8,
            "vision": 0.9
        }
        
        # Run multiple times with same inputs
        update1 = self.plugin.update(0.5, cues)
        update2 = self.plugin.update(0.5, cues)
        
        assert abs(update1.confidence_0_1 - update2.confidence_0_1) < 1e-10
        
    def test_hysteresis_behavior(self):
        """Test hysteresis behavior"""
        # Set small hysteresis for testing
        self.plugin.hysteresis = 0.01
        
        cues = {
            "track_id": "test_track",
            "rf": 0.5
        }
        
        # Small change should be held due to hysteresis
        update = self.plugin.update(0.5, cues)
        assert update.reason == "hysteresis_hold"
        assert update.confidence_0_1 == 0.5
        
        # Large change should go through
        cues["rf"] = 0.9
        update = self.plugin.update(0.5, cues)
        assert update.reason == "bayesian_update"
        assert update.confidence_0_1 != 0.5
        
    def test_vision_event_handling(self):
        """Test vision event handling"""
        track_id = "test_track"
        
        # Test vision true event
        vision_event = {"verified": True}
        update = self.plugin.update(0.5, {}, vision_event)
        
        assert update.confidence_0_1 == self.plugin.true_v
        assert update.reason == "vision_true"
        assert update.details["vision_verified"] is True
        
        # Test vision false event
        vision_event = {"verified": False}
        update = self.plugin.update(0.8, {}, vision_event)
        
        assert update.confidence_0_1 == max(self.plugin.false_v, 0.8)
        assert update.reason == "vision_false"
        assert update.details["vision_verified"] is False
        
    def test_cue_score_mapping(self):
        """Test cue score mapping"""
        # Test RF cue mapping
        rf_score = self.plugin._map_cue_score("rf", -70)  # RSSI
        assert 0 <= rf_score <= 1
        
        rf_score_bars = self.plugin._map_cue_score("rf", 7)  # Signal bars
        assert 0 <= rf_score_bars <= 1
        
        # Test vision cue mapping
        vision_score = self.plugin._map_cue_score("vision", 0.8)
        assert 0 <= vision_score <= 1
        
        # Test acoustic cue mapping
        acoustic_score = self.plugin._map_cue_score("acoustic", 80)  # SPL
        assert 0 <= acoustic_score <= 1
        
    def test_cue_weight_assignment(self):
        """Test cue weight assignment"""
        # Test RF weight
        rf_weight = self.plugin._get_cue_weight("rf")
        assert rf_weight == self.plugin.weight_rf
        
        # Test vision weight
        vision_weight = self.plugin._get_cue_weight("vision")
        assert vision_weight == self.plugin.weight_vision
        
        # Test acoustic weight
        acoustic_weight = self.plugin._get_cue_weight("acoustic")
        assert acoustic_weight == self.plugin.weight_acoustic
        
        # Test unknown cue weight
        unknown_weight = self.plugin._get_cue_weight("unknown")
        assert unknown_weight == 0.1
        
    def test_confidence_bounds(self):
        """Test confidence bounds application"""
        track_id = "test_track"
        
        # Test normal bounds
        confidence = self.plugin._apply_bounds(track_id, 0.5, 0)
        assert self.plugin.min_confidence <= confidence <= self.plugin.max_confidence
        
        # Test vision window bounds
        self.plugin.vision_true_time[track_id] = 0
        confidence = self.plugin._apply_bounds(track_id, 1.0, 1)  # Within 3 second window
        assert confidence == 1.0
        
        # Test after vision window
        confidence = self.plugin._apply_bounds(track_id, 1.0, 5)  # After 3 second window
        assert confidence <= self.plugin.max_confidence
        
    def test_timeout_decay(self):
        """Test timeout decay behavior"""
        track_id = "test_track"
        
        # Set up initial state
        self.plugin.log_odds[track_id] = math.log(0.8 / 0.2)
        self.plugin.last_update[track_id] = 0
        
        # Test timeout decay
        with patch('time.time', return_value=2.0):  # 2 seconds later
            update = self.plugin.update(0.8, {"track_id": track_id})
            
        assert update.reason == "timeout_decay"
        assert update.confidence_0_1 < 0.8  # Should decay
        
    def test_weighted_update_fallback(self):
        """Test weighted update fallback"""
        # Set fusion method to non-bayes
        self.plugin.fusion_method = "weighted"
        
        cues = {
            "track_id": "test_track",
            "rf": 0.8,
            "vision": 0.9
        }
        
        update = self.plugin.update(0.5, cues)
        
        assert update.reason == "weighted_update"
        assert 0 <= update.confidence_0_1 <= 1
        
    def test_confidence_hierarchy(self):
        """Test confidence hierarchy validation"""
        # Test valid hierarchy
        self.plugin.true_v = 1.0
        self.plugin.base = 0.75
        self.plugin.false_v = 0.5
        
        # Should not raise exception
        self.plugin._validate_confidence_hierarchy()
        
        # Test invalid hierarchy
        self.plugin.true_v = 0.5
        self.plugin.base = 0.75
        self.plugin.false_v = 1.0
        
        with pytest.raises(ValueError):
            self.plugin._validate_confidence_hierarchy()
            
    def test_weights_validation(self):
        """Test weights validation"""
        # Test valid weights
        self.plugin.weight_rf = 0.6
        self.plugin.weight_vision = 0.4
        self.plugin.weight_ir = 0.4
        self.plugin.weight_acoustic = 0.25
        
        # Should not raise exception
        self.plugin._validate_weights()
        
        # Test invalid weights (all zero)
        self.plugin.weight_rf = 0
        self.plugin.weight_vision = 0
        self.plugin.weight_ir = 0
        self.plugin.weight_acoustic = 0
        
        with pytest.raises(ValueError):
            self.plugin._validate_weights()
            
    def test_reproducible_seeds(self):
        """Test that results are reproducible with same random seeds"""
        import random
        
        # Set random seed
        random.seed(42)
        
        cues = {
            "track_id": "test_track",
            "rf": 0.8,
            "vision": 0.9
        }
        
        # Run multiple times with same seed
        update1 = self.plugin.update(0.5, cues)
        
        random.seed(42)
        update2 = self.plugin.update(0.5, cues)
        
        assert abs(update1.confidence_0_1 - update2.confidence_0_1) < 1e-10
        
    def test_edge_cases(self):
        """Test edge cases"""
        # Test with empty cues
        update = self.plugin.update(0.5, {"track_id": "test_track"})
        assert 0 <= update.confidence_0_1 <= 1
        
        # Test with extreme values
        cues = {
            "track_id": "test_track",
            "rf": 1.0,
            "vision": 0.0
        }
        update = self.plugin.update(0.5, cues)
        assert 0 <= update.confidence_0_1 <= 1
        
        # Test with invalid cue values
        cues = {
            "track_id": "test_track",
            "rf": "invalid",
            "vision": None
        }
        update = self.plugin.update(0.5, cues)
        assert 0 <= update.confidence_0_1 <= 1


class TestConfidenceFusionIntegration:
    """Integration tests for confidence fusion"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.plugin = ConfidencePlugin()
        
    def test_full_fusion_workflow(self):
        """Test complete fusion workflow"""
        track_id = "test_track"
        
        # Initial detection
        cues = {
            "track_id": track_id,
            "rf": 0.8
        }
        update1 = self.plugin.update(0.5, cues)
        
        # Add vision confirmation
        vision_event = {"verified": True}
        update2 = self.plugin.update(update1.confidence_0_1, {}, vision_event)
        
        # Add more RF data
        cues["rf"] = 0.9
        update3 = self.plugin.update(update2.confidence_0_1, cues)
        
        # Verify confidence increases over time
        assert update3.confidence_0_1 >= update2.confidence_0_1
        assert update2.confidence_0_1 >= update1.confidence_0_1
        
    def test_multiple_tracks(self):
        """Test handling multiple tracks"""
        track1 = "track_1"
        track2 = "track_2"
        
        # Update track 1
        cues1 = {
            "track_id": track1,
            "rf": 0.8
        }
        update1 = self.plugin.update(0.5, cues1)
        
        # Update track 2
        cues2 = {
            "track_id": track2,
            "rf": 0.9
        }
        update2 = self.plugin.update(0.5, cues2)
        
        # Verify tracks are independent
        assert update1.confidence_0_1 != update2.confidence_0_1
        assert track1 in self.plugin.log_odds
        assert track2 in self.plugin.log_odds
        
    def test_confidence_decay(self):
        """Test confidence decay over time"""
        track_id = "test_track"
        
        # Set up high confidence
        self.plugin.log_odds[track_id] = math.log(0.9 / 0.1)
        self.plugin.last_update[track_id] = 0
        
        # Test decay after timeout
        with patch('time.time', return_value=2.0):
            update = self.plugin.update(0.9, {"track_id": track_id})
            
        assert update.confidence_0_1 < 0.9
        assert update.reason == "timeout_decay"
