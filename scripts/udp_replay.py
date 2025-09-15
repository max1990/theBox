import os
import socket
import time


def replay(file_path: str, port: int, interval_ms: int):
    addr = ("127.0.0.1", port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            sock.sendto(line.encode("utf-8"), addr)
            time.sleep(max(0.0, interval_ms) / 1000.0)


if __name__ == "__main__":
    path = os.getenv("DRONESHIELD_INPUT_FILE", "./data/DroneShield_Detections.txt")
    port = int(os.getenv("DRONESHIELD_UDP_PORT", "56000"))
    interval = int(os.getenv("REPLAY_INTERVAL_MS", "400"))
    replay(path, port, interval)

import os, time, socket, sys, ast, json
from pathlib import Path

INPUT = os.getenv("DRONESHIELD_INPUT_FILE", "data/DroneShield_Detections.txt")
PORT  = int(os.getenv("DRONESHIELD_UDP_PORT", "56000"))
HOST  = "127.0.0.1"
INTERVAL_MS = int(os.getenv("REPLAY_INTERVAL_MS", "400"))

def main():
    p = Path(INPUT)
    if not p.exists():
        print(f"[udp_replay] Input file not found: {p}", file=sys.stderr)
        sys.exit(1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sent = 0
    with p.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Send raw line; listener will parse (dict-like, JSON, or k=v)
            sock.sendto(line.encode("utf-8"), (HOST, PORT))
            sent += 1
            time.sleep(INTERVAL_MS / 1000.0)
    print(f"[udp_replay] Sent {sent} messages to {HOST}:{PORT}")

if __name__ == "__main__":
    main()
