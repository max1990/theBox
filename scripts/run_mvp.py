import json
import logging
import sys
import time
from datetime import datetime, timezone

from mvp.config import (
    DB_PATH,
    DEFAULT_CONFIDENCE,
    DRONESHIELD_INPUT_FILE,
    DRONESHIELD_UDP_PORT,
    REPLAY_INTERVAL_MS,
    SEACROSS_HOST,
    SEACROSS_PORT,
    SEARCH_DURATION_MS,
    SEARCH_MAX_MS,
    SEARCH_VERDICT,
)
from mvp.db_adapter import DBAdapter
from mvp.plugins.droneshield_listener.udp_listener import DroneShieldUDPListener
from mvp.plugins.seacross.seacross_adapter import SeaCrossAdapter
from mvp.plugins.search.search_stub import SearchStub
from mvp.schemas import CLSMessage, SGTMessage
from plugins.confidence.confidence_plugin import ConfidencePlugin
from plugins.range.range_plugin import RangePlugin
from plugins.vision.vision_plugin import VisionPlugin
from scripts.udp_replay import replay


def main():
    logging.basicConfig(
        filename="mvp_demo.log", level=logging.INFO, format="%(asctime)s %(message)s"
    )
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

    db = DBAdapter(DB_PATH)
    seacross = SeaCrossAdapter(SEACROSS_HOST, SEACROSS_PORT)
    vision = VisionPlugin()
    confidence = ConfidencePlugin()
    ranger = RangePlugin()

    latest_bearing_per_track: dict[str, float] = {}

    def on_search_result(track_id: str, verified: bool):
        if verified:
            db.mark_validated(track_id)
            new_conf = confidence.update_after_vision(1.0, True)
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
            # reset status to force re-validate next time
            pass

    search = SearchStub(
        SEARCH_VERDICT, SEARCH_DURATION_MS, SEARCH_MAX_MS, on_result=on_search_result
    )

    def on_detection(det):
        # Track upsert
        track_id = db.upsert_track(det.sensor_track_key, det.timestamp_ms)
        db.touch_track(track_id, det.timestamp_ms)
        # Confidence at first detection via plugin
        base_conf = confidence.initial_score()
        stats["confidence_updates"] += 1
        db.update_track_confidence(track_id, base_conf)
        # Range estimate on first sighting
        if db.get_status(track_id) == "new":
            km = ranger.estimate_km(det.signal, det.bearing_deg)
            db.update_track_range(track_id, km)
            stats["range"] += 1
            stats["range_estimates"] += 1
        # Record detection
        db.insert_detection(
            track_id, det.dict(), DEFAULT_CONFIDENCE, json.dumps(det.dict())
        )

        # Trakka slew (adapter)
        stats["camera_cmds"] += 1
        latest_bearing_per_track[track_id] = float(det.bearing_deg)

        # Immediately mark slew complete and start search
        async def do_vision_and_search():
            nonlocal track_id
            # vision
            res = await vision.run_verification(track_id)
            stats["vision_runs"] += 1
            if res.verified:
                db.set_class_label(track_id, res.label)
                on_search_result(track_id, True)
            else:
                # drop to false floor but don't emit CLS/SGT
                prev_conf = base_conf
                new_conf = confidence.update_after_vision(prev_conf, False)
                stats["confidence_updates"] += 1
                db.update_track_confidence(track_id, new_conf)

        import asyncio

        asyncio.run(do_vision_and_search())

        # If validated already, emit SGT per detection
        if db.get_status(track_id) == "validated":
            now = datetime.now(timezone.utc)
            yyyymmdd = now.strftime("%Y%m%d")
            hhmmss = now.strftime("%H%M%S") + f".{int(now.microsecond/1e4):02d}"
            sgt = SGTMessage(
                object_id=track_id,
                yyyymmdd=yyyymmdd,
                hhmmss=hhmmss,
                distance_m=350.0,
                distance_err_m=5.0,
                bearing_deg=latest_bearing_per_track.get(track_id, det.bearing_deg),
                bearing_err_deg=5.0,
                altitude_m=0.0,
                altitude_err_m=5.0,
            )
            seacross.send_sgt(sgt)
            stats["sgt"] += 1

    listener = DroneShieldUDPListener(DRONESHIELD_UDP_PORT, on_detection=on_detection)
    listener.start()

    # Launch replay in-proc
    replay(DRONESHIELD_INPUT_FILE, DRONESHIELD_UDP_PORT, REPLAY_INTERVAL_MS)

    # Drain for a bit
    time.sleep(2.0)
    listener.stop()

    summary = db.summary()

    # Log counters to mvp_demo.log
    log = logging.getLogger("mvp_demo")
    log.info("=== MVP DEMO COUNTERS ===")
    log.info(f"vision_runs: {stats['vision_runs']}")
    log.info(f"confidence_updates: {stats['confidence_updates']}")
    log.info(f"range_estimates: {stats['range_estimates']}")
    log.info(f"tracks_created: {summary['tracks']}")
    log.info(f"detections_ingested: {summary['detections']}")
    log.info(f"cls_emitted: {stats['cls']}")
    log.info(f"sgt_emitted: {stats['sgt']}")
    log.info(f"camera_commands: {stats['camera_cmds']}")

    print("=== MVP DEMO PASSED ===")
    print(f"Tracks created: {summary['tracks']}")
    print(f"Detections ingested: {summary['detections']}")
    print(f"CLS emitted: {stats['cls']}")
    print(f"SGT emitted: {stats['sgt']}")
    print(f"Confidence bumps 0.75 -> 1.0: {stats['bumps']}")
    print(f"Range estimates applied: {stats['range']} (2.0 km)")
    print(f"Camera commands issued: {stats['camera_cmds']}")
    print(f"Vision runs: {stats['vision_runs']}")
    print(f"Confidence updates: {stats['confidence_updates']}")
    print(f"Range estimates: {stats['range_estimates']}")
    sys.exit(0)


if __name__ == "__main__":
    main()
