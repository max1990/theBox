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
DB_PATH = os.getenv("DB_PATH", "thebox_mvp.sqlite")
SEACROSS_HOST = os.getenv("SEACROSS_HOST", "127.0.0.1")
SEACROSS_PORT = int(os.getenv("SEACROSS_PORT", "2000"))

# Vision
VISION_VERDICT = getenv_bool("VISION_VERDICT", True)
VISION_LABEL = os.getenv("VISION_LABEL", "Quadcopter")
VISION_LATENCY_MS = int(os.getenv("VISION_LATENCY_MS", "5000"))
VISION_MAX_MS = int(os.getenv("VISION_MAX_MS", "15000"))

# Confidence
CONFIDENCE_BASE = float(os.getenv("CONFIDENCE_BASE", "0.75"))
CONFIDENCE_TRUE = float(os.getenv("CONFIDENCE_TRUE", "1.0"))
CONFIDENCE_FALSE = float(os.getenv("CONFIDENCE_FALSE", "0.5"))

# Range
RANGE_MODE = os.getenv("RANGE_MODE", "fixed")
RANGE_FIXED_KM = float(os.getenv("RANGE_FIXED_KM", "2.0"))
RANGE_RSSI_REF_DBM = float(os.getenv("RANGE_RSSI_REF_DBM", "-50"))
RANGE_RSSI_REF_KM = float(os.getenv("RANGE_RSSI_REF_KM", "2.0"))
RANGE_MIN_KM = float(os.getenv("RANGE_MIN_KM", "0.1"))
RANGE_MAX_KM = float(os.getenv("RANGE_MAX_KM", "8.0"))


