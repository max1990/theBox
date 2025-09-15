import ast
import json
from math import pi


def parse_maybe_python_dict(text: str):
    try:
        return ast.literal_eval(text)
    except Exception:
        pass
    try:
        return json.loads(text)
    except Exception:
        pass
    # key=val fallback
    data = {}
    for part in text.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            data[k.strip()] = v.strip()
    return data


def rad_to_bearing_deg(rad: float) -> float:
    deg = (rad * 180.0 / pi) % 360.0
    return deg if deg >= 0 else deg + 360.0


