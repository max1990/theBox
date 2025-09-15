import logging
import os
from mvp.schemas import ConfidenceUpdate


log = logging.getLogger("plugins.confidence")


def _f(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


class ConfidencePlugin:
    def __init__(self):
        self.base = _f("CONFIDENCE_BASE", 0.75)
        self.true_v = _f("CONFIDENCE_TRUE", 1.0)
        self.false_v = _f("CONFIDENCE_FALSE", 0.5)
        self.updates = 0

    def initial_score(self) -> float:
        self.updates += 1
        log.info("[confidence] initial=%.3f", self.base)
        return self.base

    def update_after_vision(self, prev: float, verified: bool) -> float:
        self.updates += 1
        if verified:
            updated = self.true_v
            reason = "vision_true"
        else:
            updated = max(self.false_v, prev)
            reason = "vision_false"
        log.info("[confidence] prev=%.3f updated=%.3f reason=%s", prev, updated, reason)
        return updated


