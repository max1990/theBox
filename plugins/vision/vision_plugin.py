import asyncio
import logging
import os
import platform
from dataclasses import dataclass
from pathlib import Path

from mvp.schemas import VisionResult


log = logging.getLogger("plugins.vision")


def _get_bool_env(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class VisionConfig:
    # Model configuration
    model_path: str = os.getenv("VISION_MODEL_PATH", "")
    roi: str = os.getenv("VISION_ROI", "0.0,0.0,1.0,1.0")
    frame_skip: int = int(os.getenv("VISION_FRAME_SKIP", "1"))
    n_consec_for_true: int = int(os.getenv("VISION_N_CONSEC_FOR_TRUE", "3"))
    max_dwell_ms: int = int(os.getenv("VISION_MAX_DWELL_MS", "15000"))
    sweep_step_deg: float = float(os.getenv("VISION_SWEEP_STEP_DEG", "5.0"))
    priority: int = int(os.getenv("VISION_PRIORITY", "1"))
    
    # Defaults
    verdict_default: bool = _get_bool_env("VISION_VERDICT_DEFAULT", True)
    label_default: str = os.getenv("VISION_LABEL_DEFAULT", "Quadcopter")
    latency_ms: int = int(os.getenv("VISION_LATENCY_MS", "5000"))
    max_ms: int = int(os.getenv("VISION_MAX_MS", "15000"))
    
    # Backend
    use_onnx: bool = platform.system() == "Windows"
    use_cuda: bool = platform.system() == "Windows"


class VisionPlugin:
    def __init__(self, cfg: VisionConfig | None = None):
        self.cfg = cfg or VisionConfig()
        self.runs = 0
        self.model_loaded = False
        self.onnx_session = None
        
        # Try to load ONNX model if configured
        if self.cfg.use_onnx and self.cfg.model_path:
            self._load_onnx_model()
        elif self.cfg.use_onnx and not self.cfg.model_path:
            log.warning("ONNX Runtime enabled but VISION_MODEL_PATH not set - using defaults")
        elif not self.cfg.use_onnx:
            log.info("ONNX Runtime disabled - using stub implementation")

    def _load_onnx_model(self):
        """Load ONNX model for vision processing"""
        try:
            if self.cfg.use_cuda:
                import onnxruntime as ort
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            else:
                import onnxruntime as ort
                providers = ['CPUExecutionProvider']
            
            if Path(self.cfg.model_path).exists():
                self.onnx_session = ort.InferenceSession(self.cfg.model_path, providers=providers)
                self.model_loaded = True
                log.info("ONNX model loaded successfully from %s", self.cfg.model_path)
            else:
                log.warning("ONNX model file not found at %s - using defaults", self.cfg.model_path)
        except ImportError:
            log.warning("ONNX Runtime not available - using stub implementation")
        except Exception as e:
            log.error("Failed to load ONNX model: %s - using defaults", e)

    async def run_verification(self, track_id: str | int, timeout_ms: int | None = None) -> VisionResult:
        self.runs += 1
        
        # If model is missing, return default after latency
        if not self.model_loaded and self.cfg.use_onnx:
            log.warning("Vision model not loaded - returning default verdict")
            latency = self.cfg.latency_ms
            if timeout_ms is not None:
                latency = min(latency, timeout_ms)
            await asyncio.sleep(max(0, latency) / 1000.0)
            return VisionResult(
                track_id=str(track_id), 
                verified=self.cfg.verdict_default, 
                label=self.cfg.label_default, 
                latency_ms=latency
            )
        
        # Normal processing
        latency = min(self.cfg.latency_ms, self.cfg.max_ms)
        if timeout_ms is not None:
            latency = min(latency, timeout_ms)
        await asyncio.sleep(max(0, latency) / 1000.0)
        
        # For now, use configured defaults (can be enhanced with actual ONNX inference)
        res = VisionResult(
            track_id=str(track_id), 
            verified=self.cfg.verdict_default, 
            label=self.cfg.label_default, 
            latency_ms=latency
        )
        log.info("[vision] track=%s verified=%s label=%s latency=%s", track_id, res.verified, res.label, latency)
        return res


