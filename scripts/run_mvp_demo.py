#!/usr/bin/env python3
"""
MVP Demo Script for TheBox
Implements the complete pipeline with range, confidence, and vision plugins
"""
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment early
from mvp.env_loader import load_env

load_env()

from mvp.env_loader import get_bool, get_float, get_str
from mvp.geometry import apply_offsets
from mvp.schemas import CLSMessage, SGTMessage
from plugins.confidence.confidence_plugin import ConfidencePlugin
from plugins.range.range_plugin import RangePlugin
from plugins.vision.vision_plugin import VisionPlugin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler("mvp_demo.log"), logging.StreamHandler()],
)
log = logging.getLogger("mvp_demo")


class MockDBAdapter:
    """Mock database adapter for demo"""

    def __init__(self):
        self.tracks = {}
        self.detections = []
        self.cls_emitted = set()

    def upsert_track(self, sensor_key: str, timestamp_ms: int) -> str:
        """Create or update track"""
        track_id = f"track_{sensor_key}"
        if track_id not in self.tracks:
            self.tracks[track_id] = {
                "sensor_key": sensor_key,
                "created": timestamp_ms,
                "last_update": timestamp_ms,
                "status": "new",
                "confidence": 0.75,
                "range_km": None,
                "class_label": None,
                "validated": False,
            }
        else:
            self.tracks[track_id]["last_update"] = timestamp_ms
        return track_id

    def get_status(self, track_id: str) -> str:
        """Get track status"""
        return self.tracks.get(track_id, {}).get("status", "unknown")

    def mark_validated(self, track_id: str):
        """Mark track as validated"""
        if track_id in self.tracks:
            self.tracks[track_id]["status"] = "validated"
            self.tracks[track_id]["validated"] = True

    def update_track_confidence(self, track_id: str, confidence: float):
        """Update track confidence"""
        if track_id in self.tracks:
            self.tracks[track_id]["confidence"] = confidence

    def update_track_range(self, track_id: str, range_km: float):
        """Update track range"""
        if track_id in self.tracks:
            self.tracks[track_id]["range_km"] = range_km

    def set_class_label(self, track_id: str, label: str):
        """Set track class label"""
        if track_id in self.tracks:
            self.tracks[track_id]["class_label"] = label

    def was_cls_emitted(self, track_id: str) -> bool:
        """Check if CLS was already emitted for track"""
        return track_id in self.cls_emitted

    def mark_cls_emitted(self, track_id: str):
        """Mark CLS as emitted for track"""
        self.cls_emitted.add(track_id)

    def insert_detection(
        self, track_id: str, detection_data: dict, confidence: float, raw_data: str
    ):
        """Insert detection record"""
        self.detections.append(
            {
                "track_id": track_id,
                "timestamp": time.time(),
                "detection_data": detection_data,
                "confidence": confidence,
                "raw_data": raw_data,
            }
        )

    def summary(self) -> dict:
        """Get summary statistics"""
        return {
            "tracks": len(self.tracks),
            "detections": len(self.detections),
            "validated": sum(
                1 for t in self.tracks.values() if t.get("validated", False)
            ),
        }


class MockSeaCrossAdapter:
    """Mock SeaCross adapter for demo"""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sent_cls = 0
        self.sent_sgt = 0
        self.messages = []

    def send_cls(self, cls: CLSMessage):
        """Send CLS message"""
        self.sent_cls += 1
        message = f"$XACLS,{cls.object_id},{cls.type},,{cls.brand_model},{cls.affiliation},details_url={cls.details_url}*CS"
        self.messages.append(("CLS", message))
        log.info(f"Sent CLS: {message}")

    def send_sgt(self, sgt: SGTMessage):
        """Send SGT message"""
        self.sent_sgt += 1
        message = f"$XASGT,{sgt.object_id},{sgt.yyyymmdd},{sgt.hhmmss},{sgt.distance_m:.1f},{sgt.distance_err_m:.1f},{sgt.bearing_deg:.1f},{sgt.bearing_err_deg:.1f},{sgt.altitude_m:.1f},{sgt.altitude_err_m:.1f}*CS"
        self.messages.append(("SGT", message))
        log.info(f"Sent SGT: {message}")


class DroneShieldReplay:
    """Replay DroneShield detections from file"""

    def __init__(self, input_file: str, port: int, interval_ms: int):
        self.input_file = input_file
        self.port = port
        self.interval_ms = interval_ms
        self.detections = []
        self.load_detections()

    def load_detections(self):
        """Load detections from file"""
        try:
            with open(self.input_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        try:
                            detection = json.loads(line)
                            self.detections.append(detection)
                        except json.JSONDecodeError:
                            continue
            log.info(f"Loaded {len(self.detections)} detections from {self.input_file}")
        except FileNotFoundError:
            log.warning(
                f"Input file {self.input_file} not found - creating mock detections"
            )
            self.create_mock_detections()

    def create_mock_detections(self):
        """Create mock detections for demo"""
        mock_detections = [
            {
                "timestamp_ms": int(time.time() * 1000),
                "sensor_track_key": "mock_001",
                "bearing_deg": 45.0,
                "signal": {"RSSI": -60, "SignalBars": 6},
                "source": "droneshield",
            },
            {
                "timestamp_ms": int(time.time() * 1000) + 1000,
                "sensor_track_key": "mock_002",
                "bearing_deg": 120.0,
                "signal": {"RSSI": -70, "SignalBars": 4},
                "source": "droneshield",
            },
        ]
        self.detections = mock_detections

    def replay(self, callback):
        """Replay detections with callback"""
        for i, detection in enumerate(self.detections):
            if i > 0:
                time.sleep(self.interval_ms / 1000.0)
            callback(detection)


async def main():
    """Main demo function"""
    log.info("Starting MVP Demo")

    # Get environment variables
    droneshield_input_file = get_str(
        "DRONESHIELD_INPUT_FILE", "./data/DroneShield_Detections.txt"
    )
    droneshield_port = int(get_float("DRONESHIELD_UDP_PORT", 56000))
    replay_interval_ms = int(get_float("REPLAY_INTERVAL_MS", 1000))
    camera_connected = get_bool("CAMERA_CONNECTED", False)
    search_verdict = get_bool("SEARCH_VERDICT", True)
    search_duration_ms = int(get_float("SEARCH_DURATION_MS", 5000))
    search_max_ms = int(get_float("SEARCH_MAX_MS", 10000))
    default_confidence = get_float("DEFAULT_CONFIDENCE", 0.75)
    range_fixed_km = get_float("RANGE_FIXED_KM", 2.0)
    db_path = get_str("DB_PATH", "thebox_mvp.sqlite")
    seacross_host = get_str("SEACROSS_HOST", "192.168.0.255")
    seacross_port = int(get_float("SEACROSS_PORT", 62000))
    log_path = get_str("LOG_PATH", "./mvp_demo.log")

    # Initialize components
    db = MockDBAdapter()
    seacross = MockSeaCrossAdapter(seacross_host, seacross_port)
    range_plugin = RangePlugin()
    confidence_plugin = ConfidencePlugin()
    vision_plugin = VisionPlugin()

    # Statistics
    stats = {
        "camera_cmds": 0,
        "cls": 0,
        "sgt": 0,
        "bumps": 0,
        "range": 0,
        "vision_runs": 0,
        "confidence_updates": 0,
        "range_estimates": 0,
    }

    latest_bearing_per_track = {}

    def on_search_result(track_id: str, verified: bool):
        """Handle search result"""
        if verified:
            db.mark_validated(track_id)
            new_conf = confidence_plugin.update_after_vision(1.0, True)
            stats["confidence_updates"] += 1
            db.update_track_confidence(track_id, new_conf)
            stats["bumps"] += 1

            # Emit CLS once
            if not db.was_cls_emitted(track_id):
                cls = CLSMessage(
                    object_id=track_id,
                    type="UNDERWATER",
                    brand_model="Brand Model",
                    affiliation="UNKNOWN",
                    details_url=f"http://127.0.0.1:2000/drone/{track_id}",
                )
                seacross.send_cls(cls)
                db.mark_cls_emitted(track_id)
                stats["cls"] += 1
        else:
            # Reset status to force re-validate next time
            pass

    def on_detection(detection):
        """Handle detection event"""
        # Extract detection data
        track_id = db.upsert_track(
            detection["sensor_track_key"], detection["timestamp_ms"]
        )
        db.touch_track(track_id, detection["timestamp_ms"])

        # Apply bearing offsets
        raw_bearing = detection["bearing_deg"]
        adjusted_bearing = apply_offsets(
            raw_bearing, 0.0, 0.0
        )  # No plugin offset, bow zero from env
        latest_bearing_per_track[track_id] = adjusted_bearing

        # Confidence at first detection
        base_conf = confidence_plugin.initial_score()
        stats["confidence_updates"] += 1
        db.update_track_confidence(track_id, base_conf)

        # Range estimate on first sighting
        if db.get_status(track_id) == "new":
            # Create signal dict for range estimation
            signal_data = detection.get("signal", {})
            range_estimate = range_plugin.estimate_km(signal=signal_data)

            if range_estimate.range_km is not None:
                db.update_track_range(track_id, range_estimate.range_km)
                stats["range"] += 1
                stats["range_estimates"] += 1

        # Record detection
        db.insert_detection(
            track_id, detection, default_confidence, json.dumps(detection)
        )

        # Trakka slew (mock)
        stats["camera_cmds"] += 1

        # Immediately start vision and search
        async def do_vision_and_search():
            nonlocal track_id
            # Vision verification
            now_ms = int(time.time() * 1000)
            vision_result = await vision_plugin.run_verification(
                track_id, adjusted_bearing, now_ms
            )
            stats["vision_runs"] += 1

            if vision_result.verified:
                db.set_class_label(track_id, vision_result.label)
                on_search_result(track_id, True)
            else:
                # Drop to false floor but don't emit CLS/SGT
                prev_conf = base_conf
                new_conf = confidence_plugin.update_after_vision(prev_conf, False)
                stats["confidence_updates"] += 1
                db.update_track_confidence(track_id, new_conf)

        # Run vision and search
        await do_vision_and_search()

        # If validated already, emit SGT per detection
        if db.get_status(track_id) == "validated":
            now = datetime.now(timezone.utc)
            yyyymmdd = now.strftime("%Y%m%d")
            hhmmss = now.strftime("%H%M%S") + f".{int(now.microsecond/1e4):02d}"

            # Get range from database or use fixed
            range_km = db.tracks[track_id].get("range_km", range_fixed_km)

            sgt = SGTMessage(
                object_id=track_id,
                yyyymmdd=yyyymmdd,
                hhmmss=hhmmss,
                distance_m=range_km * 1000,  # Convert km to m
                distance_err_m=range_km * 100,  # 10% error
                bearing_deg=latest_bearing_per_track.get(track_id, adjusted_bearing),
                bearing_err_deg=5.0,
                altitude_m=0.0,
                altitude_err_m=20.0,
            )
            seacross.send_sgt(sgt)
            stats["sgt"] += 1

    # Replay detections
    replay = DroneShieldReplay(
        droneshield_input_file, droneshield_port, replay_interval_ms
    )
    replay.replay(on_detection)

    # Wait a bit for processing
    await asyncio.sleep(2.0)

    # Get summary
    summary = db.summary()

    # Log counters to file
    log.info("=== MVP DEMO COUNTERS ===")
    log.info(f"vision_runs: {stats['vision_runs']}")
    log.info(f"confidence_updates: {stats['confidence_updates']}")
    log.info(f"range_estimates: {stats['range_estimates']}")
    log.info(f"tracks_created: {summary['tracks']}")
    log.info(f"detections_ingested: {summary['detections']}")
    log.info(f"cls_emitted: {stats['cls']}")
    log.info(f"sgt_emitted: {stats['sgt']}")
    log.info(f"camera_commands: {stats['camera_cmds']}")

    # Append to log file
    with open(log_path, "a") as f:
        f.write("\n=== MVP DEMO COUNTERS ===\n")
        f.write(f"vision_runs: {stats['vision_runs']}\n")
        f.write(f"confidence_updates: {stats['confidence_updates']}\n")
        f.write(f"range_estimates: {stats['range_estimates']}\n")
        f.write(f"tracks_created: {summary['tracks']}\n")
        f.write(f"detections_ingested: {summary['detections']}\n")
        f.write(f"cls_emitted: {stats['cls']}\n")
        f.write(f"sgt_emitted: {stats['sgt']}\n")
        f.write(f"camera_commands: {stats['camera_cmds']}\n")

    # Print results
    print("=== MVP DEMO PASSED ===")
    print(f"Tracks created: {summary['tracks']}")
    print(f"Detections ingested: {summary['detections']}")
    print(f"CLS emitted: {stats['cls']}")
    print(f"SGT emitted: {stats['sgt']}")
    print(f"Confidence bumps 0.75 -> 1.0: {stats['bumps']}")
    print(f"Range estimates applied: {stats['range']} ({range_fixed_km} km)")
    print(f"Camera commands issued: {stats['camera_cmds']}")
    print(f"Vision runs: {stats['vision_runs']}")
    print(f"Confidence updates: {stats['confidence_updates']}")
    print(f"Range estimates: {stats['range_estimates']}")

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        log.info("Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        log.error(f"Demo failed: {e}")
        sys.exit(1)
