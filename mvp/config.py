import os


def getenv_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


DRONESHIELD_INPUT_FILE = os.getenv("DRONESHIELD_INPUT_FILE", "./data/DroneShield_Detections.txt")
DRONESHIELD_UDP_PORT = int(os.getenv("DRONESHIELD_UDP_PORT", "56000"))
REPLAY_INTERVAL_MS = int(os.getenv("REPLAY_INTERVAL_MS", "400"))
CAMERA_CONNECTED = getenv_bool("CAMERA_CONNECTED", False)
SEARCH_VERDICT = getenv_bool("SEARCH_VERDICT", True)
SEARCH_DURATION_MS = int(os.getenv("SEARCH_DURATION_MS", "5000"))
SEARCH_MAX_MS = int(os.getenv("SEARCH_MAX_MS", "10000"))
DEFAULT_CONFIDENCE = float(os.getenv("DEFAULT_CONFIDENCE", "0.75"))
RANGE_KM = float(os.getenv("RANGE_KM", "2.0"))
DB_PATH = os.getenv("DB_PATH", "thebox_mvp.sqlite")
SEACROSS_HOST = os.getenv("SEACROSS_HOST", "127.0.0.1")
SEACROSS_PORT = int(os.getenv("SEACROSS_PORT", "2000"))


