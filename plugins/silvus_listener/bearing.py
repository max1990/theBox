def wrap360(x: float) -> float:
    return (x % 360.0 + 360.0) % 360.0

def to_true_bearing(aoa_sensor_deg: float, heading_deg: float,
                    zero_axis: str = "forward", positive: str = "cw") -> float:
    """
    Convert sensor-relative AoA into degrees TRUE using the host heading.
    Defaults assume 0° = boresight/forward.
    """
    adj = aoa_sensor_deg if positive == "cw" else -aoa_sensor_deg

    if zero_axis == "right":
        adj += 90.0
    elif zero_axis == "left":
        adj -= 90.0
    elif zero_axis == "rear":
        adj += 180.0

    return wrap360(heading_deg + adj)
