"""
Environment loader for TheBox
Loads environment variables from theBox/env/.thebox.env early in startup

Adds helpers to:
- parse/normalize env dict
- write atomically with backup
- hot-reload current process and notify subscribers
"""

import os
import shutil
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from dotenv import load_dotenv


def load_env():
    """
    Load environment variables from theBox/env/.thebox.env
    This should be called before any other imports that depend on environment variables
    """
    # Get the path to the .thebox.env file
    env_file = Path(__file__).parent.parent / "env" / ".thebox.env"

    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment from {env_file}")
    else:
        print(f"Warning: Environment file not found at {env_file}")

    return env_file.exists()


def get_float(name: str, default: float) -> float:
    """Get float environment variable with default"""
    try:
        return float(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default


def get_str(name: str, default: str) -> str:
    """Get string environment variable with default"""
    return os.getenv(name, default)


def get_bool(name: str, default: bool) -> bool:
    """Get boolean environment variable with default"""
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def load_thebox_env():
    """Legacy function name for backward compatibility"""
    return load_env()


def get_bearing_offset(plugin_name: str) -> float:
    """
    Get the bearing offset for a specific plugin
    Applies global BOW_ZERO_DEG first, then plugin-specific offset
    """
    global_offset = float(os.getenv("BOW_ZERO_DEG", "0.0"))
    plugin_offset = float(os.getenv(f"{plugin_name.upper()}_BEARING_OFFSET_DEG", "0.0"))
    return global_offset + plugin_offset


def normalize_bearing(bearing_deg: float) -> float:
    """
    Normalize bearing to [0, 360) degrees
    """
    while bearing_deg < 0:
        bearing_deg += 360
    while bearing_deg >= 360:
        bearing_deg -= 360
    return bearing_deg


def apply_bearing_offsets(bearing_deg: float, plugin_name: str) -> float:
    """
    Apply global and plugin-specific bearing offsets, then normalize
    """
    offset = get_bearing_offset(plugin_name)
    adjusted = bearing_deg + offset
    return normalize_bearing(adjusted)


# ---------- Env parsing / normalization / atomic write / hot reload ----------

_subscribers = []  # type: list[Callable[[Dict[str, str]], None]]


def subscribe_to_config(callback: Callable[[dict[str, str]], None]) -> None:
    _subscribers.append(callback)


def _notify_config_reload(env: dict[str, str]) -> None:
    for cb in list(_subscribers):
        try:
            cb(env)
        except Exception as exc:
            print(f"Config subscriber error: {exc}")


def env_paths() -> tuple[Path, Path]:
    base_dir = Path(__file__).parent.parent / "env"
    return base_dir / ".thebox.env", base_dir / ".thebox.env.example"


def parse_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            env[key.strip()] = value.strip()
    return env


def normalize_env(env: dict[str, str]) -> dict[str, object]:
    """Cast sensible types; keep unknowns as strings.
    Does not enforce validation ranges; caller should validate separately.
    """
    result: dict[str, object] = {}

    def as_int(k):
        try:
            return int(str(env.get(k, "")).strip())
        except Exception:
            return None

    def as_float(k):
        try:
            return float(str(env.get(k, "")).strip())
        except Exception:
            return None

    def as_bool(k):
        v = str(env.get(k, "")).strip().lower()
        if v in {"1", "true", "yes", "on"}:
            return True
        if v in {"0", "false", "no", "off"}:
            return False
        return None

    # Known numeric / boolean keys (non-exhaustive; safe to add)
    int_keys = {
        "SEACROSS_PORT",
        "VISION_FRAME_SKIP",
        "VISION_N_CONSEC_FOR_TRUE",
        "VISION_LATENCY_MS",
        "VISION_MAX_DWELL_MS",
        "VISION_INPUT_RES",
    }
    float_keys = {
        "BOW_ZERO_DEG",
        "DRONESHIELD_BEARING_OFFSET_DEG",
        "TRAKKA_BEARING_OFFSET_DEG",
        "VISION_BEARING_OFFSET_DEG",
        "ACOUSTIC_BEARING_OFFSET_DEG",
        "VISION_ROI_HALF_DEG",
        "VISION_SWEEP_STEP_DEG",
        "CONFIDENCE_BASE",
        "CONFIDENCE_TRUE",
        "CONFIDENCE_FALSE",
        "CONF_HYSTERESIS",
        "WEIGHT_RF",
        "WEIGHT_VISION",
        "WEIGHT_IR",
        "WEIGHT_ACOUSTIC",
        "RANGE_FIXED_KM",
        "RANGE_RSSI_REF_DBM",
        "RANGE_RSSI_REF_KM",
        "RANGE_MIN_KM",
        "RANGE_MAX_KM",
        "RANGE_EWMA_ALPHA",
        "EO_FOV_WIDE_DEG",
        "EO_FOV_NARROW_DEG",
        "IR_FOV_WIDE_DEG",
        "IR_FOV_NARROW_DEG",
    }
    bool_keys = {
        "CAMERA_CONNECTED",
    }

    for k, v in env.items():
        if k in int_keys:
            cast = as_int(k)
            result[k] = cast if cast is not None else v
        elif k in float_keys:
            cast = as_float(k)
            result[k] = cast if cast is not None else v
        elif k in bool_keys:
            cast = as_bool(k)
            result[k] = cast if cast is not None else v
        else:
            result[k] = v
    return result


def atomic_write_env(path: Path, data: dict[str, object]) -> None:
    base_dir = path.parent
    base_dir.mkdir(parents=True, exist_ok=True)
    # date-stamped backup
    if path.exists():
        ts = time.strftime("%Y%m%d%H%M%S")
        backup = base_dir / f".thebox.env.bak.{ts}"
        shutil.copy2(path, backup)

    # write temp then rename
    fd, tmp_name = tempfile.mkstemp(prefix=".thebox.env.", dir=str(base_dir))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            for k in sorted(data.keys()):
                v = data[k]
                if isinstance(v, bool):
                    v_out = "true" if v else "false"
                else:
                    v_out = str(v)
                tmp.write(f"{k}={v_out}\n")
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
        except Exception:
            pass


def reload_process_env(new_env: dict[str, object]) -> None:
    # update os.environ strings
    for k, v in new_env.items():
        os.environ[k] = str(v)
    # reload python-dotenv into process for downstream readers (optional, no-op here)
    _notify_config_reload({k: str(v) for k, v in new_env.items()})


def load_env_dict_with_fallback() -> tuple[Path, dict[str, str]]:
    env_path, example_path = env_paths()
    src = env_path if env_path.exists() else example_path
    return src, parse_env_file(src)


def list_backups() -> list[Path]:
    """List all backup files, sorted by creation time (newest first)"""
    env_path, _ = env_paths()
    backup_dir = env_path.parent
    backups = list(backup_dir.glob(".thebox.env.bak.*"))
    backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return backups


def restore_latest_backup() -> bool:
    """Restore the latest backup file. Returns True if successful."""
    backups = list_backups()
    if not backups:
        return False

    env_path, _ = env_paths()
    latest_backup = backups[0]

    try:
        # Create a backup of current file before restoring
        if env_path.exists():
            current_backup = env_path.parent / f".thebox.env.current.{int(time.time())}"
            shutil.copy2(env_path, current_backup)

        # Restore from backup
        shutil.copy2(latest_backup, env_path)

        # Reload the restored environment
        restored_env = parse_env_file(env_path)
        reload_process_env(restored_env)

        return True
    except Exception as e:
        print(f"Failed to restore backup: {e}")
        return False


def normalize_angles(env_dict: dict[str, str]) -> dict[str, str]:
    """Normalize all angle fields to [0, 360) degrees"""
    angle_fields = [
        "BOW_ZERO_DEG",
        "DRONESHIELD_BEARING_OFFSET_DEG",
        "TRAKKA_BEARING_OFFSET_DEG",
        "VISION_BEARING_OFFSET_DEG",
        "ACOUSTIC_BEARING_OFFSET_DEG",
        "VISION_SWEEP_STEP_DEG",
    ]

    result = env_dict.copy()
    for field in angle_fields:
        if field in result:
            try:
                angle = float(result[field])
                while angle < 0:
                    angle += 360
                while angle >= 360:
                    angle -= 360
                result[field] = str(angle)
            except (ValueError, TypeError):
                pass  # Keep original value if not a number

    return result
