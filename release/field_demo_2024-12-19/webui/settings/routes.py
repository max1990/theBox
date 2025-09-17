import os

from flask import abort, jsonify, redirect, render_template, request, session

from mvp.env_loader import (
    atomic_write_env,
    env_paths,
    parse_env_file,
    reload_process_env,
    restore_latest_backup,
)
from mvp.env_schema import EnvSchema
from mvp.trakka_docs import get_trakka_builtin_options


def register_routes(bp, event_manager):
    last_saved_cache = {}

    def load_current():
        env_path, example_path = env_paths()
        src = env_path if env_path.exists() else example_path
        return src, parse_env_file(src)

    def validate_and_normalize(data):
        """Validate and normalize form data using Pydantic schema"""
        try:
            # Convert form data to schema
            schema = EnvSchema.from_env_dict(data)
            # Normalize angles
            normalized = schema.normalize_angles()
            return {"ok": True, "normalized": normalized.to_env_dict(), "errors": {}}
        except Exception as e:
            # Extract field-specific errors
            errors = {}
            if hasattr(e, "errors"):
                for error in e.errors():
                    field = error["loc"][0] if error["loc"] else "unknown"
                    errors[field] = [error["msg"]]
            else:
                errors["general"] = [str(e)]
            return {"ok": False, "normalized": data, "errors": errors}

    @bp.get("/settings")
    def get_settings():
        # Minimal protection
        if os.getenv("SETTINGS_PROTECT", "false").lower() in {"1", "true", "yes", "on"}:
            if not session.get("settings_ok"):
                return render_template(
                    "settings/settings.html",
                    form_values={},
                    errors={},
                    success=False,
                    error=None,
                    require_password=True,
                    trakka_options=get_trakka_builtin_options(),
                )

        src, env_dict = load_current()
        return render_template(
            "settings/settings.html",
            form_values=env_dict,
            errors={},
            success=False,
            error=None,
            trakka_options=get_trakka_builtin_options(),
        )

    @bp.post("/settings")
    def post_settings():
        if os.getenv("SETTINGS_PROTECT", "false").lower() in {"1", "true", "yes", "on"}:
            if request.form.get("action") == "login":
                if request.form.get("password") == os.getenv("SETTINGS_PASSWORD", ""):
                    session["settings_ok"] = True
                    return redirect("/settings")
                return (
                    render_template(
                        "settings/settings.html",
                        form_values={},
                        errors={},
                        success=False,
                        error="Wrong password",
                        require_password=True,
                        trakka_options=get_trakka_builtin_options(),
                    ),
                    401,
                )
            if not session.get("settings_ok"):
                return abort(403)

        action = request.form.get("action", "save")
        env_path, _ = env_paths()

        if action == "reset":
            src, env_dict = env_paths()[1], parse_env_file(env_paths()[1])
            return render_template(
                "settings/settings.html",
                form_values=env_dict,
                errors={},
                success=False,
                error=None,
                trakka_options=get_trakka_builtin_options(),
            )

        if action == "revert":
            if restore_latest_backup():
                src, env_dict = load_current()
                return render_template(
                    "settings/settings.html",
                    form_values=env_dict,
                    errors={},
                    success=True,
                    error="Restored from latest backup",
                    trakka_options=get_trakka_builtin_options(),
                )
            else:
                return render_template(
                    "settings/settings.html",
                    form_values=last_saved_cache or parse_env_file(env_path),
                    errors={},
                    success=False,
                    error="No backup found to restore",
                    trakka_options=get_trakka_builtin_options(),
                )

        # Build a dict from posted values
        form_values = {k: v for k, v in request.form.items() if k != "action"}

        # Validate and normalize
        validation_result = validate_and_normalize(form_values)

        if action == "validate":
            if validation_result["ok"]:
                return jsonify(
                    {"ok": True, "normalized": validation_result["normalized"]}
                )
            else:
                return (
                    jsonify({"ok": False, "errors": validation_result["errors"]}),
                    400,
                )

        if not validation_result["ok"]:
            return (
                render_template(
                    "settings/settings.html",
                    form_values=form_values,
                    errors=validation_result["errors"],
                    success=False,
                    error="Validation failed",
                    trakka_options=get_trakka_builtin_options(),
                ),
                400,
            )

        # Use normalized values for saving
        normalized_values = validation_result["normalized"]

        try:
            # Write atomically and backup
            atomic_write_env(env_path, normalized_values)
            last_saved_cache.clear()
            last_saved_cache.update(normalized_values)

            # Hot reload
            reload_process_env(normalized_values)
            try:
                event_manager.publish(
                    "config",
                    {"/config/reloaded": normalized_values},
                    publisher_name="settings",
                    store_in_db=False,
                )
            except Exception:
                pass

            return render_template(
                "settings/settings.html",
                form_values=normalized_values,
                errors={},
                success=True,
                error=None,
                trakka_options=get_trakka_builtin_options(),
            )

        except Exception as e:
            return (
                render_template(
                    "settings/settings.html",
                    form_values=form_values,
                    errors={"general": [f"Save failed: {str(e)}"]},
                    success=False,
                    error="Save failed",
                    trakka_options=get_trakka_builtin_options(),
                ),
                500,
            )

    @bp.post("/settings/validate")
    def validate_settings():
        """Validate settings without saving - returns JSON"""
        form_values = {k: v for k, v in request.form.items() if k != "action"}
        result = validate_and_normalize(form_values)
        return jsonify(result)

    @bp.post("/settings/save")
    def save_settings():
        """Save settings - returns JSON"""
        form_values = {k: v for k, v in request.form.items() if k != "action"}
        validation_result = validate_and_normalize(form_values)

        if not validation_result["ok"]:
            return jsonify(validation_result), 400

        try:
            env_path, _ = env_paths()
            normalized_values = validation_result["normalized"]

            # Write atomically and backup
            atomic_write_env(env_path, normalized_values)
            last_saved_cache.clear()
            last_saved_cache.update(normalized_values)

            # Hot reload
            reload_process_env(normalized_values)
            try:
                event_manager.publish(
                    "config",
                    {"/config/reloaded": normalized_values},
                    publisher_name="settings",
                    store_in_db=False,
                )
            except Exception:
                pass

            return jsonify({"ok": True, "message": "Settings saved successfully"})

        except Exception as e:
            return jsonify({"ok": False, "error": f"Save failed: {str(e)}"}), 500

    @bp.post("/settings/revert")
    def revert_settings():
        """Revert to latest backup - returns JSON"""
        if restore_latest_backup():
            return jsonify({"ok": True, "message": "Restored from latest backup"})
        else:
            return jsonify({"ok": False, "error": "No backup found to restore"}), 404
