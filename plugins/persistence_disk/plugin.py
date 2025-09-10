from thebox.plugin_interface import PluginInterface
from flask import Blueprint, render_template, jsonify, request, redirect, url_for
import os, json, threading, time, tempfile
from datetime import datetime, timezone

DEFAULT_PATH = os.environ.get("THEBOX_STATE_PATH", "data/state.json")
DEFAULT_DIR  = os.path.dirname(DEFAULT_PATH) or "data"
SAVE_EVERY_SEC = int(os.environ.get("THEBOX_STATE_SAVE_EVERY_SEC", "3"))

# Which top-level namespaces we checkpoint
NAMESPACES = ["tracks", "detections", "sensor_id_map", "droneshield_messages"]

class DiskPersistencePlugin(PluginInterface):
    def load(self):
        os.makedirs(DEFAULT_DIR, exist_ok=True)
        self._stop = threading.Event()
        self._last_save_iso = None

        # Restore if file exists
        if os.path.exists(DEFAULT_PATH):
            try:
                with open(DEFAULT_PATH, "r", encoding="utf-8") as f:
                    snap = json.load(f)
                for key in NAMESPACES:
                    if key in snap:
                        self.event_manager.db.set(key, snap[key])
                # Touch track timestamps so pages sort nicely
                tracks = self.event_manager.db.get("tracks") or {}
                now_iso = datetime.now(timezone.utc).isoformat()
                for tid in list(tracks.keys()):
                    self.event_manager.db.set(f"tracks.{tid}.last_update", now_iso)
            except Exception as e:
                print(f"[persistence_disk] restore failed: {e}")

        # Background saver
        self._t = threading.Thread(target=self._loop, name="DiskPersistence", daemon=True)
        self._t.start()

    def unload(self):
        if getattr(self, "_stop", None):
            self._stop.set()
        if getattr(self, "_t", None):
            self._t.join(timeout=2)

    def get_blueprint(self):
        bp = Blueprint(self.name, __name__, template_folder='templates')

        @bp.get("/")
        def index():
            # Serve the page at the plugin root so the tab works
            info = self._status_dict()
            return render_template("persistence_disk_plugin.html", info=info)

        @bp.get("/status")
        def status_json():
            # Shorter relative path for the template JS if you ever add it
            return jsonify(self._status_dict())

        @bp.post("/save")
        def save_now():
            self._save_snapshot()
            # redirect back to the plugin root
            return redirect(url_for(f"{self.name}.index"), code=303)

        @bp.post("/load")
        def load_now():
            if os.path.exists(DEFAULT_PATH):
                try:
                    with open(DEFAULT_PATH, "r", encoding="utf-8") as f:
                        snap = json.load(f)
                    for key in NAMESPACES:
                        if key in snap:
                            self.event_manager.db.set(key, snap[key])
                    self._last_save_iso = datetime.now(timezone.utc).isoformat()
                except Exception as e:
                    print(f"[persistence_disk] manual load failed: {e}")
            return redirect(url_for(f"{self.name}.index"), code=303)

        return bp


    def _status_dict(self):
        try:
            sz = os.path.getsize(DEFAULT_PATH)
            mtime = datetime.fromtimestamp(os.path.getmtime(DEFAULT_PATH), tz=timezone.utc).isoformat()
        except Exception:
            sz, mtime = 0, None
        return {
            "path": DEFAULT_PATH,
            "size_bytes": sz,
            "last_modified": mtime,
            "last_save_attempt": self._last_save_iso,
            "interval_sec": SAVE_EVERY_SEC,
            "namespaces": NAMESPACES,
            "counts": {
                "tracks": len(self.event_manager.db.get("tracks") or {}),
                "detections": sum(len(v) for v in (self.event_manager.db.get("detections") or {}).values()) if self.event_manager.db.get("detections") else 0,
                "sensor_id_map": len(self.event_manager.db.get("sensor_id_map") or {}),
                "droneshield_messages": len(self.event_manager.db.get("droneshield_messages") or []),
            }
        }

    def _loop(self):
        while not self._stop.is_set():
            self._save_snapshot()
            self._stop.wait(SAVE_EVERY_SEC)

    def _save_snapshot(self):
        snap = {}
        try:
            for key in NAMESPACES:
                val = self.event_manager.db.get(key)
                if val is not None:
                    snap[key] = val
            tmpfd, tmppath = tempfile.mkstemp(prefix="state.", suffix=".json", dir=DEFAULT_DIR)
            try:
                with os.fdopen(tmpfd, "w", encoding="utf-8") as f:
                    json.dump(snap, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmppath, DEFAULT_PATH)
                self._last_save_iso = datetime.now(timezone.utc).isoformat()
            except Exception:
                try: os.remove(tmppath)
                except Exception: pass
                raise
        except Exception as e:
            print(f"[persistence_disk] save failed: {e}")
