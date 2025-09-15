import asyncio
import logging
import os
from dataclasses import dataclass

from mvp.schemas import VisionResult


log = logging.getLogger("plugins.vision")


def _get_bool_env(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class VisionConfig:
    verdict_true: bool = _get_bool_env("VISION_VERDICT", True)
    label: str = os.getenv("VISION_LABEL", "Quadcopter")
    latency_ms: int = int(os.getenv("VISION_LATENCY_MS", "5000"))
    max_ms: int = int(os.getenv("VISION_MAX_MS", "15000"))


class VisionPlugin:
    def __init__(self, cfg: VisionConfig | None = None):
        self.cfg = cfg or VisionConfig()
        self.runs = 0

    async def run_verification(self, track_id: str | int, timeout_ms: int | None = None) -> VisionResult:
        self.runs += 1
        latency = min(self.cfg.latency_ms, self.cfg.max_ms)
        if timeout_ms is not None:
            latency = min(latency, timeout_ms)
        await asyncio.sleep(max(0, latency) / 1000.0)
        res = VisionResult(track_id=str(track_id), verified=bool(self.cfg.verdict_true), label=self.cfg.label, latency_ms=latency)
        log.info("[vision] track=%s verified=%s label=%s latency=%s", track_id, res.verified, res.label, latency)
        return res


