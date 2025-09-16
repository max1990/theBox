from flask import render_template, request, jsonify, session, abort
import os
from mvp.env_loader import env_paths, parse_env_file, atomic_write_env, reload_process_env
from datetime import datetime, timezone


def _protected():
    return os.getenv("SETTINGS_PROTECT", "false").lower() in {"1","true","yes","on"}


def _require_auth():
    if _protected() and not session.get("settings_ok"):
        abort(403)


def register_routes(bp, event_manager, plugin_manager):
    # Internal helpers for pipeline steps (return dicts)
    def _do_simulate_droneshield(bearing, rssi, name, protocol):
        msg = {
            "bearing": bearing,
            "rssi_dbm": rssi,
            "name": name,
            "protocol": protocol,
            "time_utc": datetime.now(timezone.utc).isoformat()
        }
        event_manager.publish("droneshield_detection", {"detection": msg}, publisher_name="testconsole", store_in_db=True)
        return {"ok": True, "published": msg}

    def _do_slew(bearing):
        mocked = False
        try:
            trakka = plugin_manager.plugins.get("trakka_control")
            cam_connected = str(os.getenv("CAMERA_CONNECTED", "false")).lower() in {"1","true","yes","on"}
            if trakka and cam_connected and hasattr(trakka, "slew_to_bearing"):
                trakka.slew_to_bearing(bearing)
            else:
                mocked = True
        except Exception:
            mocked = True
        return {"ok": True, "mocked": mocked, "sent": {"bearing_deg": bearing}}

    def _do_vision(track_id, bearing):
        verified = str(os.getenv("VISION_VERDICT_DEFAULT", "true")).lower() in {"1","true","yes","on"}
        label = os.getenv("VISION_LABEL_DEFAULT", "Object")
        latency_ms = int(os.getenv("VISION_LATENCY_MS", "500"))
        return {"ok": True, "verified": verified, "label": label, "latency_ms": latency_ms, "track_id": track_id, "bearing_deg": bearing}

    def _do_cls(track_id, brand_model, affiliation, send_live=False):
        from plugins.seacross_sender.plugin import _wrap_sentence
        sentence = _wrap_sentence("CLS", [track_id, "RF", "", brand_model, affiliation], f"details_url=http://127.0.0.1/drone/{track_id}")
        dry_run = str(os.getenv("TEST_DRY_RUN", "true")).lower() in {"1","true","yes","on"}
        sent = False
        if not dry_run and send_live:
            try:
                sc = plugin_manager.plugins.get("seacross_sender")
                if sc and hasattr(sc, "_broadcast"):
                    sc._broadcast(sentence, note="testconsole CLS")
                    sent = True
            except Exception:
                sent = False
        return {"ok": True, "sentence": sentence, "sent": sent, "dry_run": dry_run}

    def _do_sgt(track_id, bearing, dist_m, err_m, brg_err, alt_m, alt_err, send_live=False):
        from plugins.seacross_sender.plugin import _wrap_sentence, _fmt_date_time
        yyyy, hh = _fmt_date_time(None)
        fields = [track_id, yyyy, hh, f"{dist_m:.1f}", f"{err_m:.1f}", f"{bearing:.1f}", f"{brg_err:.1f}", f"{alt_m:.1f}", f"{alt_err:.1f}"]
        sentence = _wrap_sentence("SGT", fields)
        dry_run = str(os.getenv("TEST_DRY_RUN", "true")).lower() in {"1","true","yes","on"}
        sent = False
        if not dry_run and send_live:
            try:
                sc = plugin_manager.plugins.get("seacross_sender")
                if sc and hasattr(sc, "_broadcast"):
                    sc._broadcast(sentence, note="testconsole SGT")
                    sent = True
            except Exception:
                sent = False
        return {"ok": True, "sentence": sentence, "sent": sent, "dry_run": dry_run}
    @bp.get("")
    def test_console_index():
        _require_auth()
        env_path, example_path = env_paths()
        src = env_path if env_path.exists() else example_path
        env_dict = parse_env_file(src)
        dry_run = str(env_dict.get("TEST_DRY_RUN", os.getenv("TEST_DRY_RUN", "true"))).lower() in {"1","true","yes","on"}
        return render_template("testconsole/testconsole.html", dry_run=dry_run, env_defaults=env_dict)

    # ---------------- Simulations ----------------
    @bp.post("/simulate/droneshield")
    def simulate_droneshield():
        _require_auth()
        bearing = float(request.form.get("bearing_deg", os.getenv("TEST_DEFAULT_BEARING_DEG", 45.0)))
        rssi = float(request.form.get("rssi_dbm", os.getenv("TEST_DEFAULT_RSSI_DBM", -72)))
        name = request.form.get("name", os.getenv("TEST_DEFAULT_NAME", "DJI AUT XIA"))
        protocol = request.form.get("protocol", os.getenv("TEST_DEFAULT_PROTOCOL", "FHSS"))
        try:
            out = _do_simulate_droneshield(bearing, rssi, name, protocol)
            return jsonify(out)
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @bp.post("/simulate/mara")
    def simulate_mara():
        _require_auth()
        return jsonify({"ok": True, "stub": True})

    # ---------------- Steps ----------------
    @bp.post("/step/slew")
    def step_slew():
        _require_auth()
        bearing = float(request.form.get("bearing_deg", 0))
        out = _do_slew(bearing)
        return jsonify(out)

    @bp.post("/step/vision")
    def step_vision():
        _require_auth()
        track_id = request.form.get("track_id", "test-track")
        bearing = float(request.form.get("bearing_deg", 0))
        out = _do_vision(track_id, bearing)
        return jsonify(out)

    # ---------------- SeaCross compose ----------------
    @bp.post("/step/seacross/cls")
    def step_seacross_cls():
        _require_auth()
        obj_id = request.form.get("track_id", "test-track")
        brand_model = request.form.get("brand_model", "DJI")
        affiliation = request.form.get("affiliation", "UNKNOWN")
        send_live = request.form.get("send_live") == "on"
        out = _do_cls(obj_id, brand_model, affiliation, send_live)
        return jsonify(out)

    @bp.post("/step/seacross/sgt")
    def step_seacross_sgt():
        _require_auth()
        obj_id = request.form.get("track_id", "test-track")
        bearing = float(request.form.get("bearing_deg", os.getenv("TEST_DEFAULT_BEARING_DEG", 45.0)))
        dist_m = float(request.form.get("distance_m", 1000.0))
        err_m = float(request.form.get("distance_error_m", 5.0))
        brg_err = float(request.form.get("bearing_error_deg", 2.0))
        alt_m = float(request.form.get("altitude_m", 0.0))
        alt_err = float(request.form.get("altitude_error_m", 5.0))
        send_live = request.form.get("send_live") == "on"
        out = _do_sgt(obj_id, bearing, dist_m, err_m, brg_err, alt_m, alt_err, send_live)
        return jsonify(out)

    # ---------------- All steps ----------------
    @bp.post("/run/all")
    def run_all():
        _require_auth()
        bearing = float(request.form.get("bearing_deg", os.getenv("TEST_DEFAULT_BEARING_DEG", 45.0)))
        rssi = float(request.form.get("rssi_dbm", os.getenv("TEST_DEFAULT_RSSI_DBM", -72)))
        name = request.form.get("name", os.getenv("TEST_DEFAULT_NAME", "DJI AUT XIA"))
        protocol = request.form.get("protocol", os.getenv("TEST_DEFAULT_PROTOCOL", "FHSS"))
        sim = _do_simulate_droneshield(bearing, rssi, name, protocol)
        slew = _do_slew(bearing)
        vis = _do_vision("test-track", bearing)
        cls = _do_cls("test-track", name, "UNKNOWN", False)
        sgt = _do_sgt("test-track", bearing, 1000.0, 5.0, 2.0, 0.0, 5.0, False)
        return jsonify({"ok": True, "pipeline": {"simulate": sim, "slew": slew, "vision": vis, "cls": cls, "sgt": sgt}})

    # ---------------- Settings: Trakka mode ----------------
    @bp.post("/settings/trakka_mode")
    def set_trakka_mode():
        _require_auth()
        mode = request.form.get("mode", "ours").strip().lower()
        if mode not in {"builtin", "none", "ours"}:
            return jsonify({"ok": False, "error": "invalid mode"}), 400

        env_path, _ = env_paths()
        current = parse_env_file(env_path) if env_path.exists() else {}
        current["TRAKKA_DETECTION_MODE"] = mode
        atomic_write_env(env_path, current)
        reload_process_env({"TRAKKA_DETECTION_MODE": mode})

        # If Trakka plugin loaded, let it refresh status
        trakka = plugin_manager.plugins.get("trakka_control")
        if trakka and hasattr(trakka, "on_mode_changed"):
            try:
                trakka.on_mode_changed(mode)
            except Exception:
                pass
        return jsonify({"ok": True, "mode": mode})


