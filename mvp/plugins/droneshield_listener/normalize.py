from typing import Optional, Dict, Any

from mvp.schemas import NormalizedDetection
from mvp.utils import parse_maybe_python_dict, rad_to_bearing_deg


def normalize_payload(text: str) -> Optional[NormalizedDetection]:
    obj = parse_maybe_python_dict(text)

    # Drill into Data.* if present
    data = obj.get("Data") if isinstance(obj, dict) else None
    if not isinstance(data, dict):
        return None

    ts = data.get("EpochTimeMilliSeconds") or data.get("EpochTimeMilliseconds")
    if ts is None:
        return None
    try:
        ts = int(ts)
    except Exception:
        return None

    aoa = data.get("AngleOfArrivalRadians")
    if aoa is None:
        return None
    try:
        bearing = rad_to_bearing_deg(float(aoa))
    except Exception:
        return None

    key = data.get("CorrelationKey") or data.get("SerialNumber")
    if not key:
        return None

    signal: Dict[str, Any] = {}
    for k in ["Vendor", "Name", "FrequencyHertz", "RSSI", "SignalStrength", "Modulation"]:
        if k in data:
            signal[k] = data[k]

    return NormalizedDetection(
        timestamp_ms=ts,
        bearing_deg=bearing,
        sensor_track_key=str(key),
        signal=signal or None,
    )


