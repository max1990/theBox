# trakka_ops.py — Minimal operator CLI for Trakka TC control
# Works on Windows (PowerShell/CMD).

import argparse
import math
import os
import sys
import time

# Ensure project root is on sys.path so `plugins` is importable when run from tests/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from plugins.trakka_control.tcp_sender import tcp_sender


def deg2rad(d):
    return d * math.pi / 180.0


def cmd_mode(s: tcp_sender, mode_str: str):
    """
    Set gimbal mode.
      RATE=0, CAGE=1, STOW=2, GEO=3
    """
    modes = {"RATE": 0, "CAGE": 1, "STOW": 2, "GEO": 3}
    if mode_str not in modes:
        print("Invalid mode. Use RATE|CAGE|STOW|GEO")
        sys.exit(2)
    s.set_gimbal_mode(modes[mode_str])
    print(f"Mode set to {mode_str}")


def cmd_jog(s: tcp_sender, az_rs: float, el_rs: float, ms: int):
    """
    Nudge in RATE mode with angular rates (rad/s) for a duration (ms).
    Automatically stops rates at the end.
    """
    s.set_gimbal_mode(0)  # RATE
    if az_rs:
        s.set_azimuth_rate(az_rs)
    if el_rs:
        s.set_elevation_rate(el_rs)
    time.sleep(max(ms, 0) / 1000.0)
    # stop motion
    if az_rs:
        s.set_azimuth_rate(0.0)
    if el_rs:
        s.set_elevation_rate(0.0)
    print("Jog complete.")


def cmd_point(s: tcp_sender, az_deg: float, el_deg: float):
    """
    Absolute point in CAGE mode (degrees → radians).
    """
    s.set_gimbal_mode(1)  # CAGE
    s.set_cage_az(deg2rad(az_deg))
    s.set_cage_el(deg2rad(el_deg))
    print(f"Pointed to AZ={az_deg:.2f}°, EL={el_deg:.2f}°")


def cmd_sweep(
    s: tcp_sender,
    bearing_deg: float,
    spread_deg: float,
    steps: int,
    dwell_ms: int,
    el_deg: float,
):
    """
    Sector sweep using absolute AZ waypoints at fixed EL.
    Example: bearing=45, spread=30, steps=7 → 30-degree sector around 45°, 7 points.
    """
    s.set_gimbal_mode(1)  # CAGE
    left = bearing_deg - (spread_deg / 2.0)
    right = bearing_deg + (spread_deg / 2.0)
    if steps < 2:
        steps = 2
    waypoints = [left + i * (right - left) / (steps - 1) for i in range(steps)]
    s.set_cage_el(deg2rad(el_deg))
    for azd in waypoints:
        s.set_cage_az(deg2rad(azd))
        print(f"Sweep waypoint → AZ={azd:.2f}°, EL={el_deg:.2f}° (dwell {dwell_ms} ms)")
        time.sleep(max(dwell_ms, 0) / 1000.0)
    print("Sweep complete.")


def cmd_zoom(s: tcp_sender, sensor: int, cmd_word: str, val: float):
    """
    Zoom control passthrough.
      cmd_word ∈ {RATE, HFOV, DZ_RATE, COMBINED}
      NOTE:
        - Digital zoom ratio address (0x1101/0x1201/0x1401) shows DIGITAL zoom (starts at 1.0).
        - Optical zoom may NOT change that register; use HFOV or DZ_RATE if you want to see register movement.
    """
    cmd_word = cmd_word.upper()
    s.set_zoom_rate(sensor, cmd_word, val)
    zr = s.get_zoom_status(sensor)
    print(f"Zoom cmd sent: {cmd_word} {val}; DigitalZoomRatio now: {zr:.3f}x")


def cmd_status(s: tcp_sender):
    """
    Prints mode, AZ/EL (deg), and digital zoom ratios for sensors 1..3.
    """
    mode = s.get_gimbal_mode()
    az = s.get_azimuth_status()
    el = s.get_elevation_status()
    print(f"Mode={mode}  AZ={math.degrees(az):.2f}°  EL={math.degrees(el):.2f}°")
    for sensor in (1, 2, 3):
        try:
            zr = s.get_zoom_status(sensor)
            print(f" Sensor {sensor} DigitalZoomRatio: {zr:.3f}x")
        except Exception:
            pass


def panic_recenter(s: tcp_sender):
    """
    Emergency recenter: CAGE, AZ=0°, EL=+3°. Call if camera points to nowhere useful.
    """
    s.set_gimbal_mode(1)
    s.set_cage_az(0.0)
    s.set_cage_el(deg2rad(3.0))
    print("Panic recenter → AZ=0°, EL=+3°")


def main():
    p = argparse.ArgumentParser(description="Trakka TC Ops CLI")
    p.add_argument("--host", default="169.254.1.181", help="Trakka TCP host")
    p.add_argument("--port", type=int, default=51555, help="Trakka TCP port")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("mode")
    sp.add_argument("mode", choices=["RATE", "CAGE", "STOW", "GEO"])
    sp = sub.add_parser("jog")
    sp.add_argument("--az", type=float, default=0.0)
    sp.add_argument("--el", type=float, default=0.0)
    sp.add_argument("--ms", type=int, default=1000)
    sp = sub.add_parser("point")
    sp.add_argument("--az-deg", type=float, required=True)
    sp.add_argument("--el-deg", type=float, required=True)
    sp = sub.add_parser("sweep")
    sp.add_argument("--bearing-deg", type=float, required=True)
    sp.add_argument("--spread-deg", type=float, required=True)
    sp.add_argument("--steps", type=int, required=True)
    sp.add_argument("--dwell-ms", type=int, required=True)
    sp.add_argument("--el-deg", type=float, required=True)
    sp = sub.add_parser("zoom")
    sp.add_argument("--sensor", type=int, choices=[1, 2, 3], default=1)
    sp.add_argument(
        "--cmd", choices=["RATE", "HFOV", "DZ_RATE", "COMBINED"], required=True
    )
    sp.add_argument("--val", type=float, required=True)
    sp = sub.add_parser("status")
    sp = sub.add_parser("panic_recenter")

    args = p.parse_args()
    s = tcp_sender()
    s.tcp_host = args.host
    s.tcp_port = args.port

    if args.cmd == "mode":
        cmd_mode(s, args.mode)
    elif args.cmd == "jog":
        cmd_jog(s, args.az, args.el, args.ms)
    elif args.cmd == "point":
        cmd_point(s, args.az_deg, args.el_deg)
    elif args.cmd == "sweep":
        cmd_sweep(
            s, args.bearing_deg, args.spread_deg, args.steps, args.dwell_ms, args.el_deg
        )
    elif args.cmd == "zoom":
        cmd_zoom(s, args.sensor, args.cmd, args.val)
    elif args.cmd == "status":
        cmd_status(s)
    elif args.cmd == "panic_recenter":
        panic_recenter(s)


if __name__ == "__main__":
    main()
