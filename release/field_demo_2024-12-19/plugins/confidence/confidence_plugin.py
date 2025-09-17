import logging
import math
import time

from mvp.env_loader import get_float, get_str
from mvp.schemas import ConfidenceUpdate

log = logging.getLogger("plugins.confidence")


def _sigmoid(x: float) -> float:
    """Sigmoid function: 1 / (1 + exp(-x))"""
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 1.0 if x > 0 else 0.0


class ConfidencePlugin:
    def __init__(self):
        # Environment knobs
        self.base = get_float("CONFIDENCE_BASE", 0.75)
        self.true_v = get_float("CONFIDENCE_TRUE", 1.0)
        self.false_v = get_float("CONFIDENCE_FALSE", 0.5)
        self.fusion_method = get_str("CONF_FUSION_METHOD", "bayes").strip().lower()

        # Weights for different cues
        self.weight_rf = get_float("WEIGHT_RF", 0.6)
        self.weight_vision = get_float("WEIGHT_VISION", 0.4)
        self.weight_ir = get_float("WEIGHT_IR", 0.4)
        self.weight_acoustic = get_float("WEIGHT_ACOUSTIC", 0.25)

        # Hysteresis parameters
        self.hysteresis = get_float("CONF_HYSTERESIS", 0.05)

        # Bounds
        self.min_confidence = 0.35
        self.max_confidence = 0.98

        # State tracking
        self.log_odds: dict[str, float] = {}  # track_id -> log_odds
        self.last_update: dict[str, float] = {}  # track_id -> timestamp
        self.vision_true_time: dict[str, float] = (
            {}
        )  # track_id -> timestamp when vision confirmed
        self.updates = 0

    def initial_score(self) -> float:
        """Get initial confidence score"""
        self.updates += 1
        log.info("[confidence] initial=%.3f", self.base)
        return self.base

    def update(
        self, prev_c01: float, cues: dict, vision_event: dict | None = None
    ) -> ConfidenceUpdate:
        """
        Update confidence using Bayesian log-odds fusion with hysteresis

        Args:
            prev_c01: Previous confidence [0, 1]
            cues: Dictionary of cue scores {cue_name: score}
            vision_event: Vision verification event (optional)

        Returns:
            ConfidenceUpdate with new confidence and reasoning
        """
        self.updates += 1

        # Get track ID (use a default if not provided)
        track_id = cues.get("track_id", "default")
        now = time.time()

        # Initialize log-odds if first time
        if track_id not in self.log_odds:
            self.log_odds[track_id] = math.log(prev_c01 / (1 - prev_c01))

        # Handle vision event specially
        if vision_event is not None:
            return self._handle_vision_event(track_id, prev_c01, vision_event, now)

        # Apply timeout/decay if no recent updates
        if track_id in self.last_update:
            time_since_update = now - self.last_update[track_id]
            if time_since_update > 1.0:  # 1 second timeout
                # Decay: C_t = 0.9*C_prev + 0.1*0.5
                decayed = 0.9 * prev_c01 + 0.1 * 0.5
                self.log_odds[track_id] = math.log(decayed / (1 - decayed))
                self.last_update[track_id] = now

                return ConfidenceUpdate(
                    confidence_0_1=decayed,
                    reason="timeout_decay",
                    details={"time_since_update": time_since_update},
                )

        # Bayesian fusion
        if self.fusion_method == "bayes":
            return self._bayesian_update(track_id, prev_c01, cues, now)
        else:
            # Fallback to simple weighted average
            return self._weighted_update(track_id, prev_c01, cues, now)

    def _handle_vision_event(
        self, track_id: str, prev_c01: float, vision_event: dict, now: float
    ) -> ConfidenceUpdate:
        """Handle vision verification event"""
        verified = vision_event.get("verified", False)

        if verified:
            # Vision confirmed - set to true and allow 1.0 for 3 seconds
            self.vision_true_time[track_id] = now
            new_confidence = self.true_v
            reason = "vision_true"

            # Update log-odds to match
            self.log_odds[track_id] = math.log(new_confidence / (1 - new_confidence))
        else:
            # Vision negative - apply floor but don't go below false floor
            new_confidence = max(self.false_v, prev_c01)
            reason = "vision_false"

            # Update log-odds
            self.log_odds[track_id] = math.log(new_confidence / (1 - new_confidence))

        self.last_update[track_id] = now

        return ConfidenceUpdate(
            confidence_0_1=new_confidence,
            reason=reason,
            details={"vision_verified": verified},
        )

    def _bayesian_update(
        self, track_id: str, prev_c01: float, cues: dict, now: float
    ) -> ConfidenceUpdate:
        """Bayesian log-odds fusion with hysteresis"""
        # Get current log-odds
        current_log_odds = self.log_odds[track_id]

        # Process each cue
        log_odds_delta = 0.0
        cue_details = {}

        for cue_name, score in cues.items():
            if cue_name == "track_id":
                continue

            # Map score to [0, 1] range
            s_c = self._map_cue_score(cue_name, score)

            # Get weight for this cue
            weight = self._get_cue_weight(cue_name)

            # Log-odds step: Δℓ_c = W_c * (2*s_c - 1)
            delta = weight * (2 * s_c - 1)
            log_odds_delta += delta

            cue_details[cue_name] = {
                "score": score,
                "mapped_score": s_c,
                "weight": weight,
                "delta": delta,
            }

        # Apply log-odds update
        new_log_odds = current_log_odds + log_odds_delta

        # Convert to confidence
        raw_confidence = _sigmoid(new_log_odds)

        # Apply hysteresis
        confidence_change = raw_confidence - prev_c01
        if abs(confidence_change) < self.hysteresis:
            # Change too small, keep previous
            new_confidence = prev_c01
            reason = "hysteresis_hold"
        else:
            # Apply smoothing with different rates for up/down
            if confidence_change > 0:
                # Increasing confidence
                beta = self.hysteresis
            else:
                # Decreasing confidence
                beta = 0.6 * self.hysteresis

            new_confidence = (1 - beta) * prev_c01 + beta * raw_confidence
            reason = "bayesian_update"

        # Apply bounds
        new_confidence = self._apply_bounds(track_id, new_confidence, now)

        # Update state
        self.log_odds[track_id] = new_log_odds
        self.last_update[track_id] = now

        return ConfidenceUpdate(
            confidence_0_1=new_confidence,
            reason=reason,
            details={
                "log_odds_delta": log_odds_delta,
                "raw_confidence": raw_confidence,
                "confidence_change": confidence_change,
                "cues": cue_details,
            },
        )

    def _weighted_update(
        self, track_id: str, prev_c01: float, cues: dict, now: float
    ) -> ConfidenceUpdate:
        """Simple weighted average update (fallback)"""
        total_weight = 0.0
        weighted_sum = 0.0
        cue_details = {}

        for cue_name, score in cues.items():
            if cue_name == "track_id":
                continue

            # Map score to [0, 1] range
            s_c = self._map_cue_score(cue_name, score)

            # Get weight for this cue
            weight = self._get_cue_weight(cue_name)

            weighted_sum += weight * s_c
            total_weight += weight

            cue_details[cue_name] = {
                "score": score,
                "mapped_score": s_c,
                "weight": weight,
            }

        if total_weight > 0:
            raw_confidence = weighted_sum / total_weight
        else:
            raw_confidence = prev_c01

        # Apply hysteresis
        confidence_change = raw_confidence - prev_c01
        if abs(confidence_change) < self.hysteresis:
            new_confidence = prev_c01
            reason = "hysteresis_hold"
        else:
            new_confidence = raw_confidence
            reason = "weighted_update"

        # Apply bounds
        new_confidence = self._apply_bounds(track_id, new_confidence, now)

        self.last_update[track_id] = now

        return ConfidenceUpdate(
            confidence_0_1=new_confidence,
            reason=reason,
            details={
                "raw_confidence": raw_confidence,
                "confidence_change": confidence_change,
                "cues": cue_details,
            },
        )

    def _map_cue_score(self, cue_name: str, score) -> float:
        """Map cue score to [0, 1] range"""
        try:
            score = float(score)
        except (ValueError, TypeError):
            return 0.0

        # Per-cue mappings as specified
        if cue_name in ["rf", "rssi", "signal"]:
            # RF: map RSSI to [0, 1] or use signal bars
            if -100 <= score <= -25:  # RSSI range
                return max(0.0, min(1.0, (score + 100) / 75))  # -100->0, -25->1
            elif 0 <= score <= 10:  # Signal bars
                return score / 10.0
            else:
                return 0.0
        elif cue_name in ["eo", "ir", "vision"]:
            # Vision: score is already [0, 1] or confidence
            return max(0.0, min(1.0, score))
        elif cue_name in ["acoustic", "spl"]:
            # Acoustic: map SPL to [0, 1] or use confidence
            if 40 <= score <= 120:  # SPL range
                return max(0.0, min(1.0, (score - 40) / 80))  # 40->0, 120->1
            else:
                return max(0.0, min(1.0, score))
        else:
            # Default: treat as confidence [0, 1]
            return max(0.0, min(1.0, score))

    def _get_cue_weight(self, cue_name: str) -> float:
        """Get weight for a specific cue"""
        if cue_name in ["rf", "rssi", "signal"]:
            return self.weight_rf
        elif cue_name in ["eo", "ir", "vision"]:
            return self.weight_vision
        elif cue_name in ["acoustic", "spl"]:
            return self.weight_acoustic
        else:
            return 0.1  # Default small weight

    def _apply_bounds(self, track_id: str, confidence: float, now: float) -> float:
        """Apply confidence bounds with special vision handling"""
        # Check if we're in the 3-second window after vision confirmation
        if track_id in self.vision_true_time:
            time_since_vision = now - self.vision_true_time[track_id]
            if time_since_vision <= 3.0:  # 3 seconds
                # Allow up to 1.0 during this window
                return max(self.min_confidence, min(1.0, confidence))
            else:
                # Remove the vision window
                del self.vision_true_time[track_id]

        # Normal bounds
        return max(self.min_confidence, min(self.max_confidence, confidence))

    def update_after_vision(self, prev: float, verified: bool) -> float:
        """Legacy method for backward compatibility"""
        vision_event = {"verified": verified}
        update = self.update(prev, {}, vision_event)
        return update.confidence_0_1
