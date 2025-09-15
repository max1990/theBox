import logging
import os
from typing import Optional, Dict


log = logging.getLogger("plugins.range")


def _f(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _mode() -> str:
    return os.getenv("RANGE_MODE", "fixed").strip().lower()


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


class RangePlugin:
    def __init__(self):
        self.fixed_km = _f("RANGE_FIXED_KM", 2.0)
        self.rssi_ref_dbm = _f("RANGE_RSSI_REF_DBM", -50.0)
        self.rssi_ref_km = _f("RANGE_RSSI_REF_KM", 2.0)
        self.min_km = _f("RANGE_MIN_KM", 0.1)
        self.max_km = _f("RANGE_MAX_KM", 8.0)
        self.estimates = 0

    def estimate_km(self, signal: Optional[Dict] = None, bearing_deg: float | None = None) -> float:
        self.estimates += 1
        mode = _mode()
        rssi = None
        if signal and isinstance(signal, dict):
            rssi = signal.get("RSSI")
            try:
                if rssi is not None:
                    rssi = float(rssi)
            except Exception:
                rssi = None

        value_fixed = self.fixed_km
        value_rssi = None
        if rssi is not None:
            # Simple inverse heuristic: stronger (less negative) rssi -> shorter range
            delta = self.rssi_ref_dbm - rssi  # if rssi=-60 and ref=-50 => delta=-(-10)=? actually  -50 - (-60) = 10
            value_rssi = _clamp(self.rssi_ref_km + (delta * 0.05), self.min_km, self.max_km)

        if mode == "fixed" or value_rssi is None:
            km = value_fixed
        elif mode == "rssi":
            km = value_rssi
        else:  # hybrid
            km = (value_fixed + value_rssi) / 2.0

        km = _clamp(km, self.min_km, self.max_km)
        log.info("[range] range=%.3fkm mode=%s rssi=%s", km, mode, rssi)
        return km


