from flask import render_template, request, abort, session, redirect
import os
from mvp.env_loader import (
    env_paths,
    parse_env_file,
    normalize_env,
    atomic_write_env,
    reload_process_env,
)
from pathlib import Path
import ipaddress


def register_routes(bp, event_manager):
    last_saved_cache = {}

    def load_current():
        env_path, example_path = env_paths()
        src = env_path if env_path.exists() else example_path
        return src, parse_env_file(src)

    def validate(data):
        errors = {}

        def getf(k):
            try:
                return float(data.get(k, ""))
            except Exception:
                errors[k] = "Must be a number"
                return None

        def geti(k):
            try:
                return int(str(data.get(k, "")).strip())
            except Exception:
                errors[k] = "Must be an integer"
                return None

        def getb(k):
            v = str(data.get(k, "")).strip().lower()
            if v in {"true", "1", "yes", "on"}:
                return True
            if v in {"false", "0", "no", "off"}:
                return False
            errors[k] = "Must be true/false"
            return None

        # Networking
        host = data.get("SEACROSS_HOST", "").strip()
        try:
            if host:
                if host != "255.255.255.255":
                    ipaddress.IPv4Address(host)
        except Exception:
            errors["SEACROSS_HOST"] = "Must be IPv4 or 255.255.255.255"
        port = geti("SEACROSS_PORT")
        if port is not None and not (1 <= port <= 65535):
            errors["SEACROSS_PORT"] = "Out of range"

        # Offsets and angles
        for k in [
            "BOW_ZERO_DEG","DRONESHIELD_BEARING_OFFSET_DEG","TRAKKA_BEARING_OFFSET_DEG",
            "VISION_BEARING_OFFSET_DEG","ACOUSTIC_BEARING_OFFSET_DEG","VISION_ROI_HALF_DEG",
            "VISION_SWEEP_STEP_DEG"
        ]:
            v = getf(k)
            if v is None:
                continue
            if k == "VISION_ROI_HALF_DEG":
                if not (0 <= v <= 180):
                    errors[k] = "Must be within 0-180"

        # Confidence
        base = getf("CONFIDENCE_BASE")
        t = getf("CONFIDENCE_TRUE")
        f = getf("CONFIDENCE_FALSE")
        if None not in (base, t, f):
            for k, val in [("CONFIDENCE_BASE", base), ("CONFIDENCE_TRUE", t), ("CONFIDENCE_FALSE", f)]:
                if not (0 <= val <= 1):
                    errors[k] = "Must be within [0,1]"
            if t is not None and base is not None and f is not None:
                if not (t >= base >= f):
                    errors["CONFIDENCE_BASE"] = "Enforce TRUE ≥ BASE ≥ FALSE"
        h = getf("CONF_HYSTERESIS")
        if h is not None and not (0 < h < 1):
            errors["CONF_HYSTERESIS"] = "Must be in (0,1)"
        weights = [getf("WEIGHT_RF"), getf("WEIGHT_VISION"), getf("WEIGHT_IR"), getf("WEIGHT_ACOUSTIC")]
        if all(w is not None for w in weights):
            if any(w < 0 for w in weights):
                errors["WEIGHTS"] = "Weights must be non-negative"
            if sum(weights) == 0:
                errors["WEIGHTS"] = "At least one weight must be positive"

        # Range
        rng_min = getf("RANGE_MIN_KM")
        rng_max = getf("RANGE_MAX_KM")
        if None not in (rng_min, rng_max):
            if not (0 < rng_min < rng_max <= 50):
                errors["RANGE_MIN_KM"] = "0 < MIN < MAX ≤ 50"
                errors["RANGE_MAX_KM"] = "0 < MIN < MAX ≤ 50"
        fixed = getf("RANGE_FIXED_KM")
        if fixed is not None and None not in (rng_min, rng_max):
            if not (rng_min <= fixed <= rng_max):
                errors["RANGE_FIXED_KM"] = "Must be within [MIN, MAX]"
        alpha = getf("RANGE_EWMA_ALPHA")
        if alpha is not None and not (0 < alpha < 1):
            errors["RANGE_EWMA_ALPHA"] = "Must be in (0,1)"

        # Vision specifics
        res = geti("VISION_INPUT_RES")
        if res is not None and res not in {320,416,512,640,896,960}:
            errors["VISION_INPUT_RES"] = "Invalid input resolution"
        if (v := geti("VISION_FRAME_SKIP")) is not None and v < 0:
            errors["VISION_FRAME_SKIP"] = ">= 0"
        if (v := geti("VISION_N_CONSEC_FOR_TRUE")) is not None and v < 1:
            errors["VISION_N_CONSEC_FOR_TRUE"] = ">= 1"
        if (v := geti("VISION_LATENCY_MS")) is not None and v < 50:
            errors["VISION_LATENCY_MS"] = ">= 50"
        if (v := geti("VISION_MAX_DWELL_MS")) is not None and v < 1000:
            errors["VISION_MAX_DWELL_MS"] = ">= 1000"

        # Booleans
        for k in ["CAMERA_CONNECTED"]:
            if k in data:
                getb(k)

        return errors

    @bp.get("/settings")
    def get_settings():
        # Minimal protection
        if os.getenv("SETTINGS_PROTECT", "false").lower() in {"1","true","yes","on"}:
            if not session.get("settings_ok"):
                return render_template(
                    "settings/settings.html",
                    form_values={}, errors={}, success=False, error=None, require_password=True
                )
        src, env_dict = load_current()
        return render_template(
            "settings/settings.html",
            form_values=env_dict,
            errors={},
            success=False,
            error=None,
        )

    @bp.post("/settings")
    def post_settings():
        if os.getenv("SETTINGS_PROTECT", "false").lower() in {"1","true","yes","on"}:
            if request.form.get("action") == "login":
                if request.form.get("password") == os.getenv("SETTINGS_PASSWORD", ""):
                    session["settings_ok"] = True
                    return redirect("/settings")
                return render_template("settings/settings.html", form_values={}, errors={}, success=False, error="Wrong password", require_password=True), 401
            if not session.get("settings_ok"):
                return abort(403)
        action = request.form.get("action", "save")
        env_path, _ = env_paths()
        if action == "reset":
            src, env_dict = env_paths()[1], parse_env_file(env_paths()[1])
            return render_template("settings/settings.html", form_values=env_dict, errors={}, success=False, error=None)
        if action == "revert":
            env_dict = last_saved_cache or parse_env_file(env_path)
            return render_template("settings/settings.html", form_values=env_dict, errors={}, success=False, error=None)

        # Build a dict from posted values
        form_values = {k: v for k, v in request.form.items() if k != "action"}
        errors = validate(form_values)
        if errors:
            return render_template("settings/settings.html", form_values=form_values, errors=errors, success=False, error="Validation failed"), 400

        if action == "validate":
            return render_template("settings/settings.html", form_values=form_values, errors={}, success=True, error=None)

        # Normalize some angles into [0,360)
        for k in ["BOW_ZERO_DEG","DRONESHIELD_BEARING_OFFSET_DEG","TRAKKA_BEARING_OFFSET_DEG","VISION_BEARING_OFFSET_DEG","ACOUSTIC_BEARING_OFFSET_DEG","VISION_SWEEP_STEP_DEG"]:
            if k in form_values:
                try:
                    v = float(form_values[k])
                    while v < 0:
                        v += 360
                    while v >= 360:
                        v -= 360
                    form_values[k] = str(v)
                except Exception:
                    pass

        # Write atomically and backup
        atomic_write_env(env_path, form_values)
        last_saved_cache.clear()
        last_saved_cache.update(form_values)

        # Hot reload
        reload_process_env(form_values)
        try:
            event_manager.publish("config", {"/config/reloaded": form_values}, publisher_name="settings", store_in_db=False)
        except Exception:
            pass

        return render_template("settings/settings.html", form_values=form_values, errors={}, success=True, error=None)


