from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from typing import Optional, Dict, Any


class DBAdapter:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._use_sqlite = True
        # Try to detect real theBox DB – current repo provides in-memory; we fall back to sqlite
        self._ensure_sqlite()

    # ---------------- SQLite schema ----------------
    def _ensure_sqlite(self):
        with self._conn() as con:
            cur = con.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tracks (
                  track_id TEXT PRIMARY KEY,
                  sensor_track_key TEXT UNIQUE,
                  first_seen_ms INT,
                  last_seen_ms INT,
                  fused_confidence REAL,
                  last_range_km REAL,
                  lat REAL,
                  lon REAL,
                  status TEXT,
                  class_label TEXT NULL,
                  cls_emitted INT DEFAULT 0
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS detections (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  track_id TEXT,
                  timestamp_ms INT,
                  source TEXT,
                  bearing_deg REAL,
                  lat REAL,
                  lon REAL,
                  raw_json TEXT,
                  confidence REAL
                )
                """
            )
            con.commit()

    def _conn(self):
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        return sqlite3.connect(self.db_path)

    # ---------------- API ----------------
    def _stable_uuid(self, sensor_key: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, sensor_key))

    def upsert_track(self, sensor_track_key: str, first_seen_ms: int) -> str:
        with self._lock, self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT track_id FROM tracks WHERE sensor_track_key=?", (sensor_track_key,))
            row = cur.fetchone()
            if row:
                track_id = row[0]
                cur.execute("UPDATE tracks SET last_seen_ms=? WHERE track_id=?", (first_seen_ms, track_id))
            else:
                track_id = self._stable_uuid(sensor_track_key)
                cur.execute(
                    "INSERT INTO tracks(track_id, sensor_track_key, first_seen_ms, last_seen_ms, fused_confidence, status) VALUES (?,?,?,?,?,?)",
                    (track_id, sensor_track_key, first_seen_ms, first_seen_ms, 0.0, "new"),
                )
            con.commit()
            return track_id

    def update_track_confidence(self, track_id: str, fused_confidence: float):
        with self._lock, self._conn() as con:
            con.execute("UPDATE tracks SET fused_confidence=? WHERE track_id=?", (fused_confidence, track_id))
            con.commit()

    def update_track_range(self, track_id: str, range_km: float):
        with self._lock, self._conn() as con:
            con.execute("UPDATE tracks SET last_range_km=? WHERE track_id=?", (range_km, track_id))
            con.commit()

    def touch_track(self, track_id: str, last_seen_ms: int):
        with self._lock, self._conn() as con:
            con.execute("UPDATE tracks SET last_seen_ms=? WHERE track_id=?", (last_seen_ms, track_id))
            con.commit()

    def mark_validated(self, track_id: str):
        with self._lock, self._conn() as con:
            con.execute("UPDATE tracks SET status='validated' WHERE track_id=?", (track_id,))
            con.commit()

    def mark_cls_emitted(self, track_id: str):
        with self._lock, self._conn() as con:
            con.execute("UPDATE tracks SET cls_emitted=1 WHERE track_id=?", (track_id,))
            con.commit()

    def insert_detection(self, track_id: str, detection: Dict[str, Any], confidence: float, raw_json: str):
        with self._lock, self._conn() as con:
            con.execute(
                "INSERT INTO detections(track_id, timestamp_ms, source, bearing_deg, lat, lon, raw_json, confidence) VALUES (?,?,?,?,?,?,?,?)",
                (
                    track_id,
                    int(detection.get("timestamp_ms") or 0),
                    str(detection.get("source") or ""),
                    float(detection.get("bearing_deg") or 0.0),
                    detection.get("lat"),
                    detection.get("lon"),
                    raw_json,
                    float(confidence),
                ),
            )
            con.commit()

    def set_class_label(self, track_id: str, label: str | None):
        with self._lock, self._conn() as con:
            con.execute("UPDATE tracks SET class_label=? WHERE track_id=?", (label, track_id))
            con.commit()

    def get_track_by_sensor_key(self, sensor_track_key: str) -> Optional[str]:
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT track_id FROM tracks WHERE sensor_track_key=?", (sensor_track_key,))
            row = cur.fetchone()
            return row[0] if row else None

    def get_status(self, track_id: str) -> Optional[str]:
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT status FROM tracks WHERE track_id=?", (track_id,))
            row = cur.fetchone()
            return row[0] if row else None

    def was_cls_emitted(self, track_id: str) -> bool:
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT cls_emitted FROM tracks WHERE track_id=?", (track_id,))
            row = cur.fetchone()
            return bool(row[0]) if row else False

    def summary(self) -> Dict[str, int]:
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT COUNT(*), SUM(cls_emitted) FROM tracks")
            tracks_count, cls_sum = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM detections")
            detections_count = cur.fetchone()[0]
        return {
            "tracks": int(tracks_count or 0),
            "detections": int(detections_count or 0),
            "cls": int(cls_sum or 0),
        }


