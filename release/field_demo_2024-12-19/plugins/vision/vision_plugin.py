import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from mvp.env_loader import get_bool, get_float, get_str
from mvp.geometry import compute_roi_sector, normalize_deg
from mvp.schemas import VisionResult

log = logging.getLogger("plugins.vision")


@dataclass
class Detection:
    """Single detection from YOLO"""

    bbox: tuple[float, float, float, float]  # (x1, y1, x2, y2)
    confidence: float
    class_id: int
    class_name: str


@dataclass
class Track:
    """Track state for SORT/IoU tracking"""

    track_id: int
    bbox: tuple[float, float, float, float]
    confidence: float
    class_name: str
    last_seen: float
    consecutive_detections: int
    age: int


class VisionPlugin:
    def __init__(self):
        # Environment knobs
        self.backend = get_str("VISION_BACKEND", "cpu").strip().lower()
        self.model_path = get_str("VISION_MODEL_PATH", "")
        self.input_res = get_float("VISION_INPUT_RES", 640)
        self.roi_half_deg = get_float("VISION_ROI_HALF_DEG", 15)
        self.frame_skip = int(get_float("VISION_FRAME_SKIP", 2))
        self.n_consec_for_true = int(get_float("VISION_N_CONSEC_FOR_TRUE", 3))
        self.latency_ms = int(get_float("VISION_LATENCY_MS", 5000))
        self.max_dwell_ms = int(get_float("VISION_MAX_DWELL_MS", 7000))
        self.sweep_step_deg = get_float("VISION_SWEEP_STEP_DEG", 12)
        self.priority = get_str("VISION_PRIORITY", "rf_power").strip().lower()
        self.verdict_default = get_bool("VISION_VERDICT_DEFAULT", True)
        self.label_default = get_str("VISION_LABEL_DEFAULT", "Object")

        # Capture settings
        self.capture_api = get_str("CAPTURE_API", "opencv").strip().lower()
        self.capture_res = get_str("CAPTURE_RES", "1920x1080@30")
        self.bow_zero_deg = get_float("BOW_ZERO_DEG", 0.0)
        self.bearing_offset_deg = get_float("VISION_BEARING_OFFSET_DEG", 0.0)

        # FOV settings
        self.eo_fov_wide = get_float("EO_FOV_WIDE_DEG", 54.0)
        self.eo_fov_narrow = get_float("EO_FOV_NARROW_DEG", 2.0)
        self.ir_fov_wide = get_float("IR_FOV_WIDE_DEG", 27.0)
        self.ir_fov_narrow = get_float("IR_FOV_NARROW_DEG", 1.3)

        # State
        self.runs = 0
        self.model_loaded = False
        self.onnx_session = None
        self.tracks: dict[int, Track] = {}
        self.next_track_id = 1
        self.frame_count = 0
        self.current_bearing = 0.0
        self.dwell_start_time = 0.0
        self.last_capture_time = 0.0

        # Try to load ONNX model
        self._load_onnx_model()

    def _load_onnx_model(self):
        """Load ONNX model for vision processing"""
        if not self.model_path:
            log.warning("VISION_MODEL_PATH not set - using default verdict")
            return

        try:
            import onnxruntime as ort

            # Set up providers based on backend
            if self.backend == "cuda":
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            else:
                providers = ["CPUExecutionProvider"]

            if Path(self.model_path).exists():
                self.onnx_session = ort.InferenceSession(
                    self.model_path, providers=providers
                )
                self.model_loaded = True
                log.info("ONNX model loaded successfully from %s", self.model_path)
            else:
                log.warning(
                    "ONNX model file not found at %s - using defaults", self.model_path
                )
        except ImportError:
            log.warning("ONNX Runtime not available - using default verdict")
        except Exception as e:
            log.error("Failed to load ONNX model: %s - using defaults", e)

    async def run_verification(
        self, track_id: str | int, bearing_deg: float, now_ms: int
    ) -> VisionResult:
        """
        Run vision verification for a track

        Args:
            track_id: Track identifier
            bearing_deg: Bearing to look at
            now_ms: Current timestamp in milliseconds

        Returns:
            VisionResult with verification outcome
        """
        self.runs += 1
        track_id_str = str(track_id)

        # Apply bearing offsets
        adjusted_bearing = bearing_deg + self.bow_zero_deg + self.bearing_offset_deg
        self.current_bearing = normalize_deg(adjusted_bearing)

        # Check if model is missing
        if not self.model_loaded:
            log.warning("Vision model not loaded - returning default verdict")
            return VisionResult(
                verified=self.verdict_default,
                label=self.label_default,
                latency_ms=self.latency_ms,
            )

        # Check latency cap
        if now_ms - self.last_capture_time > self.latency_ms:
            log.warning("Latency exceeded - returning default verdict")
            return VisionResult(
                verified=self.verdict_default,
                label=self.label_default,
                latency_ms=now_ms - self.last_capture_time,
            )

        # Check dwell timeout
        if now_ms - self.dwell_start_time > self.max_dwell_ms:
            log.info("Max dwell time exceeded - signaling sweep")
            return VisionResult(
                verified=False,
                label="sweep_needed",
                latency_ms=now_ms - self.dwell_start_time,
                tracker={"sweep_step_deg": self.sweep_step_deg},
            )

        # Frame skip logic
        self.frame_count += 1
        if self.frame_count % (self.frame_skip + 1) != 0:
            # Skip this frame
            return VisionResult(verified=False, label="frame_skipped", latency_ms=0)

        # Capture frame
        frame = await self._capture_frame()
        if frame is None:
            return VisionResult(verified=False, label="capture_failed", latency_ms=0)

        # Compute ROI
        roi_bounds = self._compute_roi_bounds()

        # Run detection
        detections = await self._run_detection(frame, roi_bounds)

        # Update tracking
        self._update_tracking(detections, now_ms / 1000.0)

        # Check for verification
        verified_track = self._check_verification(track_id_str)

        if verified_track:
            return VisionResult(
                verified=True,
                label=verified_track.class_name,
                latency_ms=now_ms - self.last_capture_time,
                bbox=verified_track.bbox,
                tracker={
                    "track_id": verified_track.track_id,
                    "consecutive_detections": verified_track.consecutive_detections,
                    "age": verified_track.age,
                },
            )
        else:
            return VisionResult(
                verified=False,
                label="not_verified",
                latency_ms=now_ms - self.last_capture_time,
            )

    async def _capture_frame(self) -> np.ndarray | None:
        """Capture frame from camera"""
        try:
            if self.capture_api == "opencv":

                # Mock capture for now - in real implementation would use actual camera
                # Return a dummy frame
                return np.zeros((1080, 1920, 3), dtype=np.uint8)
            elif self.capture_api == "decklink":
                # Mock DeckLink capture
                return np.zeros((1080, 1920, 3), dtype=np.uint8)
            else:
                log.error("Unknown capture API: %s", self.capture_api)
                return None
        except Exception as e:
            log.error("Failed to capture frame: %s", e)
            return None

    def _compute_roi_bounds(self) -> tuple[float, float, float, float]:
        """Compute ROI bounds based on bearing and FOV"""
        # Use EO FOV as default
        fov_deg = self.eo_fov_wide

        # Compute sector bounds
        start_angle, end_angle = compute_roi_sector(
            self.current_bearing, fov_deg, self.roi_half_deg
        )

        # Convert to pixel coordinates (assuming 1920x1080 frame)
        frame_width = 1920
        frame_height = 1080

        # Convert angles to pixel positions
        start_x = int((start_angle / 360.0) * frame_width)
        end_x = int((end_angle / 360.0) * frame_width)

        # Use full height for now
        start_y = 0
        end_y = frame_height

        return (start_x, start_y, end_x, end_y)

    async def _run_detection(
        self, frame: np.ndarray, roi_bounds: tuple[float, float, float, float]
    ) -> list[Detection]:
        """Run YOLO detection on frame ROI"""
        if not self.onnx_session:
            return []

        try:
            # Extract ROI
            x1, y1, x2, y2 = roi_bounds
            roi_frame = frame[int(y1) : int(y2), int(x1) : int(x2)]

            if roi_frame.size == 0:
                return []

            # Resize to input resolution
            input_size = int(self.input_res)
            roi_resized = cv2.resize(roi_frame, (input_size, input_size))

            # Preprocess
            input_tensor = roi_resized.astype(np.float32) / 255.0
            input_tensor = np.transpose(input_tensor, (2, 0, 1))  # HWC to CHW
            input_tensor = np.expand_dims(input_tensor, axis=0)  # Add batch dimension

            # Run inference
            input_name = self.onnx_session.get_inputs()[0].name
            outputs = self.onnx_session.run(None, {input_name: input_tensor})

            # Parse outputs (assuming YOLOv8 format)
            detections = self._parse_yolo_outputs(outputs[0], roi_bounds)

            return detections

        except Exception as e:
            log.error("Detection failed: %s", e)
            return []

    def _parse_yolo_outputs(
        self, outputs: np.ndarray, roi_bounds: tuple[float, float, float, float]
    ) -> list[Detection]:
        """Parse YOLO outputs into Detection objects"""
        detections = []

        # YOLOv8 output format: [batch, 84, 8400] where 84 = 4 (bbox) + 80 (classes)
        if len(outputs.shape) != 3:
            return detections

        # Transpose to [batch, 8400, 84]
        outputs = np.transpose(outputs, (0, 2, 1))

        # Get confidence scores for all classes
        conf_scores = outputs[0, :, 4:]  # [8400, 80]
        max_conf = np.max(conf_scores, axis=1)

        # Filter by confidence threshold
        conf_threshold = 0.30  # EO threshold
        valid_indices = np.where(max_conf > conf_threshold)[0]

        for idx in valid_indices:
            # Get bbox coordinates
            x_center, y_center, width, height = outputs[0, idx, :4]

            # Convert to corner coordinates
            x1 = x_center - width / 2
            y1 = y_center - height / 2
            x2 = x_center + width / 2
            y2 = y_center + height / 2

            # Get class
            class_scores = conf_scores[idx]
            class_id = np.argmax(class_scores)
            confidence = class_scores[class_id]

            # Apply NMS threshold
            if confidence > 0.45:  # NMS IoU threshold
                detection = Detection(
                    bbox=(x1, y1, x2, y2),
                    confidence=confidence,
                    class_id=class_id,
                    class_name="Object",  # Could map class_id to actual names
                )
                detections.append(detection)

        return detections

    def _update_tracking(self, detections: list[Detection], timestamp: float):
        """Update SORT/IoU tracking"""
        # Simple tracking implementation
        for detection in detections:
            # Find best matching track
            best_track = None
            best_iou = 0.0

            for track in self.tracks.values():
                iou = self._compute_iou(detection.bbox, track.bbox)
                if iou > best_iou and iou > 0.30:  # IoU threshold
                    best_iou = iou
                    best_track = track

            if best_track:
                # Update existing track
                best_track.bbox = detection.bbox
                best_track.confidence = detection.confidence
                best_track.class_name = detection.class_name
                best_track.last_seen = timestamp
                best_track.consecutive_detections += 1
                best_track.age += 1
            else:
                # Create new track
                new_track = Track(
                    track_id=self.next_track_id,
                    bbox=detection.bbox,
                    confidence=detection.confidence,
                    class_name=detection.class_name,
                    last_seen=timestamp,
                    consecutive_detections=1,
                    age=1,
                )
                self.tracks[self.next_track_id] = new_track
                self.next_track_id += 1

        # Remove old tracks
        current_time = timestamp
        tracks_to_remove = []
        for track_id, track in self.tracks.items():
            if current_time - track.last_seen > 30.0:  # 30 second timeout
                tracks_to_remove.append(track_id)

        for track_id in tracks_to_remove:
            del self.tracks[track_id]

    def _compute_iou(
        self,
        bbox1: tuple[float, float, float, float],
        bbox2: tuple[float, float, float, float],
    ) -> float:
        """Compute IoU between two bounding boxes"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

        # Compute intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)

        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0

        intersection = (x2_i - x1_i) * (y2_i - y1_i)

        # Compute union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection

        if union <= 0:
            return 0.0

        return intersection / union

    def _check_verification(self, track_id: str) -> Track | None:
        """Check if any track meets verification criteria"""
        for track in self.tracks.values():
            if track.consecutive_detections >= self.n_consec_for_true:
                return track
        return None
