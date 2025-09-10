# plugins/seacross_sender/plugin.py
"""
SeaCross Sender (final, vendor-agnostic)

This plugin ONLY formats & broadcasts SeaCross-compatible NMEA-like sentences
for the two message types SeaCross consumes:
  • CLS  ($XACLS …)  – classification; sent once per object, re-sent if affiliation changes
  • SGT  ($XASGT …)  – position update by bearing+distance (+ optional altitude)

It subscribes to already-normalized core events (no vendor specifics here):
  • object.classification
      {
        object_id: str,            # stable id for the object (uuid hex etc.)
        domain: "AIR"|"SURFACE"|"UNDERWATER"|"UNKNOWN",
        type: str,                 # e.g., "RF" | "RemoteID" | "Radar"
        brand: str,                # e.g., "DJI"
        model: str,                # e.g., "Mavic 3"
        affiliation: str,          # "UNKNOWN"|"FRIENDLY"|"ENEMY"|"NOT_DRONE"
        details_url: str,          # optional; fallback computed as http://<host>:<port>/drone/<object_id>
        confidence: int            # optional 0..100
      }

  • object.sighting.relative       (ready for SGT; bearing+distance present)
      {
        object_id: str,
        time_utc: str,             # ISO-8601; if missing we use 'now'
        distance_m: float,
        distance_error_m: float,   # +- error (m)
        bearing_deg_true: float,   # degrees true
        bearing_error_deg: float,  # +- error (deg)
        altitude_m: float,         # optional; default 0.0
        altitude_error_m: float,   # optional; default 5.0
        confidence: int,           # optional 0..100
        range_is_synthetic: bool,  # optional; for operator awareness
        range_method: str          # optional; e.g., "rf_strength_v1"
      }

All “thinking” (vendor parsing, range estimation for RF-only bearings, fusion, AI, etc.)
happens elsewhere in the core pipeline. This plugin just reflects those normalized events
into SeaCross sentences over UDP broadcast.

Environment knobs:
  THEBOX_TALKER_ID          -> two-letter talker id (e.g., "XA") if you want to force it
  THEBOX_BROADCAST_IP       -> default "192.168.0.255"
  THEBOX_BROADCAST_PORT     -> default "62000"
  THEBOX_WEB_HOST           -> used to build default details_url (fallback: config.host or "127.0.0.1")
  THEBOX_WEB_PORT           -> used to build default details_url (fallback: config.port or 80)
"""

from thebox.plugin_interface import PluginInterface
from flask import Blueprint, jsonify, render_template
from datetime import datetime, timezone
from collections import deque
import os
import platform
import socket
import threading

# --------------------------- Dynamic talker id ---------------------------

def _default_talker_id() -> str:
    """
    Choose talker ID:
      1) THEBOX_TALKER_ID env (two ASCII letters)
      2) First two letters of hostname (letters only)
      3) Fallback "XA"
    """
    env = os.getenv("THEBOX_TALKER_ID")
    if env and len(env) == 2 and env.isalpha():
        return env.upper()
    host = (platform.node() or "").upper()
    letters = "".join(ch for ch in host if ch.isalpha())
    return letters[:2] if len(letters) >= 2 else "XA"

TALKER_ID      = _default_talker_id()
BROADCAST_IP   = os.getenv("THEBOX_BROADCAST_IP", "192.168.0.255")
BROADCAST_PORT = int(os.getenv("THEBOX_BROADCAST_PORT", "62000"))


# --------------------------- NMEA helpers ---------------------------

def _nmea_checksum(payload: str) -> str:
    c = 0
    for ch in payload:
        c ^= ord(ch)
    return f"{c:02X}"

def _wrap_sentence(sentence_type: str, fields: list[str], extra_info: str | None = None) -> str:
    """
    Build a $<TALKER><TYPE>,<fields>[,<extra>]*CS sentence.
      sentence_type: "CLS" or "SGT"
      fields: list of pre-formatted strings (no checksum, no $)
      extra_info: optional trailing field (e.g., "details_url=http://...")
    """
    stem = f"{TALKER_ID}{sentence_type}"
    payload = stem + "," + ",".join(fields)
    if extra_info:
        payload += f",{extra_info}"
    cs = _nmea_checksum(payload)
    return f"${payload}*{cs}"

def _fmt_date_time(iso_or_none: str | None) -> tuple[str, str]:
    """
    Convert ISO timestamp → (YYYYMMDD, HHMMSS.hh)
    If missing/unparseable, uses current UTC time.
    """
    try:
        iso = iso_or_none or ""
        if iso.endswith("Z"):
            iso = iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso) if iso else datetime.now(timezone.utc)
    except Exception:
        dt = datetime.now(timezone.utc)
    yyyymmdd = dt.strftime("%Y%m%d")
    # Hundredths of seconds in .hh
    hhmmss = dt.strftime("%H%M%S") + f".{int(dt.microsecond/1e4):02d}"
    return yyyymmdd, hhmmss

def _s(x, default="") -> str:
    """Safe string."""
    return default if x is None else str(x)


# ======================================================================
#                              PLUGIN
# ======================================================================

class SeaCrossSenderPlugin(PluginInterface):
    """
    Vendor-agnostic SeaCross sender.
    Subscribes to:
      • object.classification
      • object.sighting.relative
    Emits over UDP broadcast:
      • $XACLS … (once per object id unless affiliation changes)
      • $XASGT … (for every relative sighting)
    Also mirrors useful fields into the in-memory DB (tracks/ & detections/).
    """

    # ----------------------- Lifecycle -----------------------
    def __init__(self, event_manager):
        super().__init__(event_manager)
        self.lock = threading.Lock()
        self.sent_nmea = deque(maxlen=300)
        self.errors = deque(maxlen=200)
        self.cls_aff_sent = {}  # object_id -> last affiliation we emitted

        # UDP broadcast socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def load(self):
        # Subscribe to normalized core events (no vendor-specific code here)
        self.event_manager.subscribe("object.classification", "payload", self.on_classification, 1)
        self.event_manager.subscribe("object.sighting.relative", "payload", self.on_sighting_relative, 1)
        print(f"SeaCross Sender loaded. Talker={TALKER_ID}, target={BROADCAST_IP}:{BROADCAST_PORT}")

    def unload(self):
        try:
            self.sock.close()
        except Exception:
            pass
        print("SeaCross Sender unloaded.")

    # ----------------------- Event handlers -----------------------

    def on_classification(self, event_type, path, p: dict):
        """
        Normalize & emit $XACLS exactly once per object id (re-emit on affiliation change).
        Also updates track headers in DB for the Labels UI & persistence.
        """
        try:
            obj_id = _s(p.get("object_id")).strip()
            if not obj_id:
                return

            # Track header fields (mirror into DB)
            domain = _s(p.get("domain"), "UNKNOWN").upper()
            type_  = _s(p.get("type"))
            brand  = _s(p.get("brand"))
            model  = _s(p.get("model"))
            aff    = _s(p.get("affiliation"), "UNKNOWN").upper()
            conf   = p.get("confidence")
            details_url = self._resolve_details_url(obj_id, p.get("details_url"))

            # Write/refresh track core fields
            self.event_manager.db.set(f"tracks.{obj_id}.affiliation", aff)
            self.event_manager.db.set(f"tracks.{obj_id}.details_url", details_url)
            self.event_manager.db.set(f"tracks.{obj_id}.domain", domain)
            self.event_manager.db.set(f"tracks.{obj_id}.brand", brand)
            self.event_manager.db.set(f"tracks.{obj_id}.model", model)
            if isinstance(conf, (int, float)):
                self.event_manager.db.set(f"tracks.{obj_id}.fused_confidence", int(conf))
            self.event_manager.db.set(f"tracks.{obj_id}.last_update", datetime.now(timezone.utc).isoformat())

            # Emit CLS once (re-emit if affiliation changes)
            last_aff = self.cls_aff_sent.get(obj_id)
            if last_aff != aff:
                brand_model = (brand + " " + model).strip()
                # Format per your captures:
                # $XACLS,<ID>,<TYPE>,,<BRAND MODEL>,<AFFILIATION>,details_url=...*CS
                fields = [obj_id, type_, "", brand_model, aff]
                extra  = f"details_url={details_url}"
                sentence = _wrap_sentence("CLS", fields, extra)
                self._broadcast(sentence, note=f"CLS {obj_id} {brand_model} {aff}")
                self.cls_aff_sent[obj_id] = aff

        except Exception as e:
            self._log_error(f"on_classification error: {e}")

    def on_sighting_relative(self, event_type, path, p: dict):
        """
        Emit $XASGT for each relative sighting (bearing + distance present).
        Also updates fused_* fields in DB and appends a detection record.
        """
        try:
            obj_id = _s(p.get("object_id")).strip()
            if not obj_id:
                return

            # Required values
            if p.get("distance_m") is None or p.get("bearing_deg_true") is None:
                # If someone sent a bearing-only event to this channel by mistake, skip gracefully.
                self._log_error(f"relative sighting missing distance/bearing for {obj_id}; skipping SGT")
                return

            distance_m = float(p["distance_m"])
            bearing_deg = float(p["bearing_deg_true"])

            # Optional values with sensible defaults
            time_utc = p.get("time_utc")
            dist_err = float(p.get("distance_error_m", 5.0))
            brg_err  = float(p.get("bearing_error_deg", 2.0))
            alt_m    = float(p.get("altitude_m", 0.0)) if p.get("altitude_m") is not None else 0.0
            alt_err  = float(p.get("altitude_error_m", 5.0))
            conf     = p.get("confidence")
            synth    = p.get("range_is_synthetic")
            method   = p.get("range_method")

            # Build SGT
            yyyymmdd, hhmmss = _fmt_date_time(time_utc)
            # $XASGT,<ID>,<YYYYMMDD>,<HHMMSS.hh>,<DIST>,<DIST_ERR>,<BRG>,<BRG_ERR>,<ALT>,<ALT_ERR>*CS
            fields = [
                obj_id,
                yyyymmdd,
                hhmmss,
                f"{distance_m:.1f}",
                f"{dist_err:.1f}",
                f"{bearing_deg:.1f}",
                f"{brg_err:.1f}",
                f"{alt_m:.1f}",
                f"{alt_err:.1f}",
            ]
            sentence = _wrap_sentence("SGT", fields)
            self._broadcast(sentence, note=f"SGT {obj_id} d={distance_m:.1f}m brg={bearing_deg:.1f}° alt={alt_m:.1f}m")

            # Mirror fused state for UI/persistence
            self._update_track_state(obj_id, bearing_deg=bearing_deg, distance_m=distance_m, alt_m=alt_m)
            if isinstance(conf, (int, float)):
                self.event_manager.db.set(f"tracks.{obj_id}.fused_confidence", int(conf))
            if synth is not None:
                self.event_manager.db.set(f"tracks.{obj_id}.range_is_synthetic", bool(synth))
            if method:
                self.event_manager.db.set(f"tracks.{obj_id}.range_method", str(method))

            # Append a minimal detection record (useful for audit/post-mission)
            self._append_detection(obj_id, time_utc=time_utc, bearing_deg=bearing_deg,
                                   distance_m=distance_m, alt_m=alt_m, confidence=conf)

        except Exception as e:
            self._log_error(f"on_sighting_relative error: {e}")

    # ----------------------- DB helpers -----------------------

    def _resolve_details_url(self, obj_id: str, provided: str | None) -> str:
        """
        Prefer the provided details_url; else build http://<host>:<port>/drone/<obj_id>
        host/port from config if available, else env, else defaults.
        """
        if provided:
            return provided
        host = (getattr(self.event_manager, "config", {}) or {}).get("host") or os.getenv("THEBOX_WEB_HOST") or "127.0.0.1"
        port = (getattr(self.event_manager, "config", {}) or {}).get("port") or os.getenv("THEBOX_WEB_PORT") or 80
        try:
            port = int(port)
        except Exception:
            port = 80
        return f"http://{host}:{port}/drone/{obj_id}"

    def _update_track_state(self, obj_id, *, bearing_deg=None, distance_m=None, alt_m=None):
        """Write fused_* + last_update without clobbering unknowns."""
        if bearing_deg is not None:
            self.event_manager.db.set(f"tracks.{obj_id}.fused_bearing_deg", float(bearing_deg))
        if distance_m is not None:
            self.event_manager.db.set(f"tracks.{obj_id}.fused_distance_m", float(distance_m))
        if alt_m is not None:
            self.event_manager.db.set(f"tracks.{obj_id}.fused_altitude_m", float(alt_m))
        self.event_manager.db.set(f"tracks.{obj_id}.last_update", datetime.now(timezone.utc).isoformat())

    def _append_detection(self, obj_id, *, time_utc=None, bearing_deg=None, distance_m=None, alt_m=None, confidence=None):
        det_id = str(int(datetime.now(timezone.utc).timestamp() * 1000))  # epoch ms
        base = f"detections.{obj_id}.{det_id}"
        if time_utc:
            self.event_manager.db.set(f"{base}.time_utc", time_utc)
        if bearing_deg is not None:
            self.event_manager.db.set(f"{base}.bearing_deg", float(bearing_deg))
        if distance_m is not None:
            self.event_manager.db.set(f"{base}.distance_m", float(distance_m))
        if alt_m is not None:
            self.event_manager.db.set(f"{base}.altitude_m", float(alt_m))
        if isinstance(confidence, (int, float)):
            self.event_manager.db.set(f"{base}.confidence", int(confidence))

    # ----------------------- UDP + logging -----------------------

    def _broadcast(self, sentence: str, note: str = ""):
        try:
            self.sock.sendto(sentence.encode("ascii", errors="ignore"), (BROADCAST_IP, BROADCAST_PORT))
            with self.lock:
                self.sent_nmea.append({
                    "t": datetime.now(timezone.utc).isoformat(),
                    "sentence": sentence,
                    "note": note
                })
        except Exception as e:
            self._log_error(f"broadcast error: {e}")

    def _log_error(self, message: str):
        with self.lock:
            self.errors.append({
                "t": datetime.now(timezone.utc).isoformat(),
                "err": str(message)
            })

    # ----------------------- Flask blueprint -----------------------

    def get_blueprint(self):
        bp = Blueprint(self.name, __name__, template_folder='templates')

        @bp.get("/")
        def index():
            # Pass values the template expects
            return render_template(
                "seacross_sender_plugin.html",
                talker_id=TALKER_ID,
                broadcast_ip=BROADCAST_IP,
                broadcast_port=BROADCAST_PORT,
                # also pass these aliases in case your template uses different names
                target_ip=BROADCAST_IP,
                target_port=BROADCAST_PORT,
            )


        @bp.get("/status")
        def status():
            with self.lock:
                def map_err(e):
                    # our internal keys are "t" and "err"
                    return {
                        "timestamp": e.get("t") or e.get("timestamp"),
                        "message": e.get("err") or e.get("message"),
                    }

                def map_nmea(n):
                    # our internal keys are "t", "sentence", "note"
                    ts = n.get("t") or n.get("timestamp")
                    sentence = (n.get("sentence") or n.get("details") or "")
                    # infer type for your "Type" column
                    typ = "SGT" if "XASGT" in sentence else ("CLS" if "XACLS" in sentence else "")
                    details = n.get("note") or sentence
                    return {"timestamp": ts, "type": typ, "details": details}

                return jsonify({
                    # your template reads these fields:
                    "target_ip": BROADCAST_IP,
                    "target_port": BROADCAST_PORT,

                    # optional extra if you want to display it later
                    "talker_id": TALKER_ID,

                    # tables:
                    "errors": [map_err(e) for e in list(self.errors)],
                    # we don't track received_events in this plugin; send an empty array so the table renders
                    "received_events": [],
                    "sent_nmea": [map_nmea(n) for n in list(self.sent_nmea)],
                })


        return bp