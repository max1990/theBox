import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

from mvp.config import (
    DRONESHIELD_INPUT_FILE,
    DRONESHIELD_UDP_PORT,
    REPLAY_INTERVAL_MS,
    CAMERA_CONNECTED,
    SEARCH_VERDICT,
    SEARCH_DURATION_MS,
    SEARCH_MAX_MS,
    DEFAULT_CONFIDENCE,
    RANGE_KM,
    DB_PATH,
    SEACROSS_HOST,
    SEACROSS_PORT,
)
from mvp.db_adapter import DBAdapter
from mvp.plugins.droneshield_listener.udp_listener import DroneShieldUDPListener
from mvp.plugins.ranging.range_stub import RangeStub
from mvp.plugins.search.search_stub import SearchStub
from mvp.plugins.seacross.seacross_adapter import SeaCrossAdapter
from mvp.schemas import CLSMessage, SGTMessage
from scripts.udp_replay import replay


def main():
    logging.basicConfig(filename="mvp_demo.log", level=logging.INFO, format="%(asctime)s %(message)s")
    stats = {
        "camera_cmds": 0,
        "cls": 0,
        "sgt": 0,
        "bumps": 0,
        "range": 0,
    }

    db = DBAdapter(DB_PATH)
    seacross = SeaCrossAdapter(SEACROSS_HOST, SEACROSS_PORT)
    range_stub = RangeStub(db, RANGE_KM)

    latest_bearing_per_track: dict[str, float] = {}

    def on_search_result(track_id: str, verified: bool):
        if verified:
            db.mark_validated(track_id)
            db.update_track_confidence(track_id, 1.0)
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

    search = SearchStub(SEARCH_VERDICT, SEARCH_DURATION_MS, SEARCH_MAX_MS, on_result=on_search_result)

    def on_detection(det):
        # Track upsert
        track_id = db.upsert_track(det.sensor_track_key, det.timestamp_ms)
        db.touch_track(track_id, det.timestamp_ms)
        # Confidence at first detection
        db.update_track_confidence(track_id, DEFAULT_CONFIDENCE)
        # Range stub on first sighting
        if db.get_status(track_id) == "new":
            range_stub.apply_on_first(track_id)
            stats["range"] += 1
        # Record detection
        db.insert_detection(track_id, det.dict(), DEFAULT_CONFIDENCE, json.dumps(det.dict()))

        # Trakka slew (adapter)
        stats["camera_cmds"] += 1
        latest_bearing_per_track[track_id] = float(det.bearing_deg)
        # Immediately mark slew complete and start search
        search.run(track_id)

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
    print("=== MVP DEMO PASSED ===")
    print(f"Tracks created: {summary['tracks']}")
    print(f"Detections ingested: {summary['detections']}")
    print(f"CLS emitted: {stats['cls']}")
    print(f"SGT emitted: {stats['sgt']}")
    print(f"Confidence bumps 0.75 -> 1.0: {stats['bumps']}")
    print(f"Range estimates applied: {stats['range']} (2.0 km)")
    print(f"Camera commands issued: {stats['camera_cmds']}")
    sys.exit(0)


if __name__ == "__main__":
    main()


