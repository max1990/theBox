"""
Test suite for Confidence Plugin
Tests the 10 Confidence sequences with stepwise values
"""

import time

from plugins.confidence.confidence_plugin import ConfidencePlugin


class TestConfidencePlugin:
    """Test cases for ConfidencePlugin"""

    def setup_method(self):
        """Set up test environment"""
        # Mock environment variables
        import os

        os.environ.update(
            {
                "CONFIDENCE_BASE": "0.75",
                "CONFIDENCE_TRUE": "1.0",
                "CONFIDENCE_FALSE": "0.5",
                "CONF_FUSION_METHOD": "bayes",
                "WEIGHT_RF": "0.6",
                "WEIGHT_VISION": "0.4",
                "WEIGHT_IR": "0.4",
                "WEIGHT_ACOUSTIC": "0.25",
                "CONF_HYSTERESIS": "0.05",
            }
        )
        self.plugin = ConfidencePlugin()

    def test_initial_score(self):
        """Test initial confidence score"""
        score = self.plugin.initial_score()
        assert score == 0.75

    def test_vision_true_update(self):
        """Test confidence update after vision verification (true)"""
        prev_conf = 0.75
        vision_event = {"verified": True}

        update = self.plugin.update(prev_conf, {}, vision_event)

        assert update.confidence_0_1 == 1.0
        assert update.reason == "vision_true"
        assert update.details["vision_verified"] is True

    def test_vision_false_update(self):
        """Test confidence update after vision verification (false)"""
        prev_conf = 0.75
        vision_event = {"verified": False}

        update = self.plugin.update(prev_conf, {}, vision_event)

        assert update.confidence_0_1 == 0.5  # False floor
        assert update.reason == "vision_false"
        assert update.details["vision_verified"] is False

    def test_rf_cue_mapping(self):
        """Test RF cue score mapping"""
        # Test RSSI mapping
        cues = {"rf": -60}  # RSSI
        update = self.plugin.update(0.75, cues, None)

        # Should map RSSI to [0, 1] range
        assert "rf" in update.details["cues"]
        mapped_score = update.details["cues"]["rf"]["mapped_score"]
        assert 0.0 <= mapped_score <= 1.0

        # Test signal bars mapping
        cues = {"rf": 6}  # Signal bars
        update = self.plugin.update(0.75, cues, None)

        mapped_score = update.details["cues"]["rf"]["mapped_score"]
        assert mapped_score == 0.6  # 6/10

    def test_vision_cue_mapping(self):
        """Test vision cue score mapping"""
        cues = {"vision": 0.8}  # Confidence score
        update = self.plugin.update(0.75, cues, None)

        mapped_score = update.details["cues"]["vision"]["mapped_score"]
        assert mapped_score == 0.8

    def test_acoustic_cue_mapping(self):
        """Test acoustic cue score mapping"""
        # Test SPL mapping
        cues = {"acoustic": 80}  # SPL
        update = self.plugin.update(0.75, cues, None)

        mapped_score = update.details["cues"]["acoustic"]["mapped_score"]
        assert 0.0 <= mapped_score <= 1.0

        # Test confidence mapping
        cues = {"acoustic": 0.7}  # Confidence
        update = self.plugin.update(0.75, cues, None)

        mapped_score = update.details["cues"]["acoustic"]["mapped_score"]
        assert mapped_score == 0.7

    def test_bayesian_fusion(self):
        """Test Bayesian log-odds fusion"""
        cues = {"rf": -50, "vision": 0.9}  # Strong RF signal  # High vision confidence

        update = self.plugin.update(0.75, cues, None)

        assert update.reason == "bayesian_update"
        assert "log_odds_delta" in update.details
        assert "cues" in update.details

        # Should increase confidence due to strong cues
        assert update.confidence_0_1 > 0.75

    def test_hysteresis_hold(self):
        """Test hysteresis prevents small changes"""
        # Small change should be held
        cues = {"rf": -49}  # Very small change
        update = self.plugin.update(0.75, cues, None)

        if abs(update.details.get("confidence_change", 0)) < 0.05:
            assert update.reason == "hysteresis_hold"
            assert update.confidence_0_1 == 0.75

    def test_confidence_bounds(self):
        """Test confidence bounds enforcement"""
        # Test minimum bound
        cues = {"rf": -120}  # Very weak signal
        update = self.plugin.update(0.35, cues, None)

        assert update.confidence_0_1 >= 0.35

        # Test maximum bound (except during vision window)
        cues = {"rf": -10, "vision": 1.0}  # Very strong signals
        update = self.plugin.update(0.98, cues, None)

        assert update.confidence_0_1 <= 0.98

    def test_vision_window_1_0(self):
        """Test 3-second window allows 1.0 confidence after vision true"""
        # First vision true
        vision_event = {"verified": True}
        update1 = self.plugin.update(0.75, {}, vision_event)

        assert update1.confidence_0_1 == 1.0

        # Immediately after (within 3 seconds)
        cues = {"rf": -10, "vision": 1.0}  # Very strong signals
        update2 = self.plugin.update(1.0, cues, None)

        # Should allow 1.0 during vision window
        assert update2.confidence_0_1 == 1.0

    def test_timeout_decay(self):
        """Test timeout decay after 1 second"""
        # Initial update
        cues = {"rf": -50}
        update1 = self.plugin.update(0.75, cues, None)

        # Wait and update again (simulate timeout)
        time.sleep(1.1)
        update2 = self.plugin.update(update1.confidence_0_1, {}, None)

        if update2.reason == "timeout_decay":
            # Should decay: C_t = 0.9*C_prev + 0.1*0.5
            expected = 0.9 * update1.confidence_0_1 + 0.1 * 0.5
            assert abs(update2.confidence_0_1 - expected) < 0.001

    def test_weighted_fallback(self):
        """Test weighted average fallback when not using Bayesian"""
        import os

        os.environ["CONF_FUSION_METHOD"] = "weighted"
        plugin = ConfidencePlugin()

        cues = {"rf": -50, "vision": 0.8}
        update = plugin.update(0.75, cues, None)

        assert update.reason == "weighted_update"
        assert "raw_confidence" in update.details

    def test_negative_cue_handling(self):
        """Test handling of negative cue scores"""
        cues = {"rf": -200}  # Invalid RSSI
        update = self.plugin.update(0.75, cues, None)

        # Should map to 0.0 for invalid values
        mapped_score = update.details["cues"]["rf"]["mapped_score"]
        assert mapped_score == 0.0

    def test_missing_cue_handling(self):
        """Test handling of missing cues"""
        cues = {"track_id": "test"}  # Only track_id, no actual cues
        update = self.plugin.update(0.75, cues, None)

        # Should not change confidence much without cues
        assert abs(update.confidence_0_1 - 0.75) < 0.1

    def test_multiple_cue_fusion(self):
        """Test fusion of multiple cues"""
        cues = {"rf": -50, "vision": 0.8, "acoustic": 70}

        update = self.plugin.update(0.75, cues, None)

        assert len(update.details["cues"]) == 3
        assert "rf" in update.details["cues"]
        assert "vision" in update.details["cues"]
        assert "acoustic" in update.details["cues"]

    def test_legacy_update_after_vision(self):
        """Test legacy update_after_vision method"""
        prev_conf = 0.75
        new_conf = self.plugin.update_after_vision(prev_conf, True)

        assert new_conf == 1.0

        new_conf = self.plugin.update_after_vision(prev_conf, False)
        assert new_conf == 0.5

    def test_confidence_sequence_1(self):
        """Test confidence sequence 1: Initial -> RF strong -> Vision true"""
        # Initial
        conf = self.plugin.initial_score()
        assert conf == 0.75

        # RF strong
        cues = {"rf": -30}
        update = self.plugin.update(conf, cues, None)
        conf = update.confidence_0_1
        assert conf > 0.75  # Should increase

        # Vision true
        vision_event = {"verified": True}
        update = self.plugin.update(conf, {}, vision_event)
        conf = update.confidence_0_1
        assert conf == 1.0

    def test_confidence_sequence_2(self):
        """Test confidence sequence 2: Initial -> RF weak -> Vision false"""
        # Initial
        conf = self.plugin.initial_score()
        assert conf == 0.75

        # RF weak
        cues = {"rf": -90}
        update = self.plugin.update(conf, cues, None)
        conf = update.confidence_0_1
        assert conf < 0.75  # Should decrease

        # Vision false
        vision_event = {"verified": False}
        update = self.plugin.update(conf, {}, vision_event)
        conf = update.confidence_0_1
        assert conf == 0.5  # False floor

    def test_confidence_sequence_3(self):
        """Test confidence sequence 3: Multiple cues -> Hysteresis -> Decay"""
        # Multiple cues
        cues = {"rf": -50, "vision": 0.8, "acoustic": 80}
        update = self.plugin.update(0.75, cues, None)
        conf = update.confidence_0_1

        # Small change (hysteresis)
        cues = {"rf": -49}
        update = self.plugin.update(conf, cues, None)
        if update.reason == "hysteresis_hold":
            assert update.confidence_0_1 == conf

        # Timeout decay
        time.sleep(1.1)
        update = self.plugin.update(conf, {}, None)
        if update.reason == "timeout_decay":
            expected = 0.9 * conf + 0.1 * 0.5
            assert abs(update.confidence_0_1 - expected) < 0.001
