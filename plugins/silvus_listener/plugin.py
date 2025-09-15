"""
Silvus Listener Plugin
======================

Minimal "frequency → bearing(s)" integration for TheBox:
- Ingest Silvus AoA detections (from replayed text logs or a live UDP feed).
- Convert sensor-relative AoA(s) + host heading → bearing(s) in degrees TRUE.
- Publish normalized `object.sighting.directional` events (bearing-only).
"""

import os, sys
import threading
from collections import deque
from typing import Dict, Optional


from flask import Blueprint, render_template, jsonify
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from thebox.plugin_interface import PluginInterface

from .config import SilvusConfig
from .parser import parse_lines
from .bearing import to_true_bearing
from .live_udp_client import SilvusUDPClient, example_protobuf_decoder


class SilvusListenerPlugin(PluginInterface):
    """Conformant plugin class for Silvus AoA ingestion."""

    def __init__(self, name, event_manager):
        super().__init__(name, event_manager)

        # Read config; can be overridden via environment variables.
        self.cfg = SilvusConfig(
            replay_path=os.getenv("SILVUS_REPLAY_PATH") or None,
        )

        self._replay_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

        # Optional live UDP intake
        self._udp: Optional[SilvusUDPClient] = None

        # A small ring buffer of recent bearings for the UI table
        self._last_bearings: deque = deque(maxlen=self.cfg.status_buffer_max)

    # ---------- Plugin lifecycle ----------
    def load(self):
        """Start background ingestion based on environment/config."""
        # Start replay if configured
        if self.cfg.replay_path and os.path.exists(self.cfg.replay_path):
            self._replay_thread = threading.Thread(
                target=self._run_replay, name="SilvusReplay", daemon=True
            )
            self._replay_thread.start()

        # Start live UDP listener if configured
        udp_host = os.getenv("SILVUS_UDP_HOST")
        udp_port = os.getenv("SILVUS_UDP_PORT")
        udp_mode = (os.getenv("SILVUS_UDP_MODE", "text") or "text").lower()

        if udp_host and udp_port:
            decoder = None
            if udp_mode == "protobuf":
                decoder = example_protobuf_decoder  # replace when .proto is available

            self._udp = SilvusUDPClient(
                host=udp_host,
                port=int(udp_port),
                mode=udp_mode,
                on_record=self._emit_bearing,
                decoder=decoder,
            )
            self._udp.start()

    def unload(self):
        """Stop background workers and free resources."""
        self._stop.set()

        if self._udp:
            try:
                self._udp.stop()
            finally:
                self._udp = None

        if self._replay_thread:
            self._replay_thread.join(timeout=2.0)
            self._replay_thread = None

    # ---------- Web UI ----------
    def get_blueprint(self):
        """Expose a minimal UI and a JSON status endpoint."""
        bp = Blueprint(self.name, __name__, template_folder="templates")

        @bp.route("/")
        def index():
            return render_template("silvus_listener.html")

        @bp.route("/status")
        def status():
            return jsonify({"last_bearings": list(self._last_bearings)})

        return bp

    # ---------- Core logic ----------
    def _emit_bearing(self, rec: Dict):
        """
        Convert a Silvus record into one or two directional sighting events.
        Expected keys: time_utc, freq_mhz, aoa1_deg, aoa2_deg, heading_deg.
        """
        heading = rec.get("heading_deg")
        if heading is None:
            # No heading → cannot produce degrees TRUE reliably.
            return

        for key in ("aoa1_deg", "aoa2_deg"):
            aoa = rec.get(key)
            if aoa is None:
                continue

            bearing_true = to_true_bearing(
                aoa, heading, zero_axis=self.cfg.zero_axis, positive=self.cfg.positive
            )

            event = {
                "time_utc": rec["time_utc"],
                "freq_mhz": rec["freq_mhz"],
                "bearing_deg_true": bearing_true,
                "bearing_error_deg": self.cfg.default_bearing_error_deg,
                "confidence": self.cfg.default_confidence,
            }

            self.publish("object.sighting.directional", event, store_in_db=True)
            self._last_bearings.append(event)

    # ---------- Background workers ----------
    def _run_replay(self):
        """Replay a Silvus text log file if configured via SILVUS_REPLAY_PATH."""
        try:
            with open(self.cfg.replay_path, "r", encoding="utf-8") as f:
                for rec in parse_lines(f):
                    if self._stop.is_set():
                        break
                    self._emit_bearing(rec)
        except Exception:
            # Keep quiet during bring-up; use host logger in production
            pass
