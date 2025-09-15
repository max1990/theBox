import socket
import threading
from typing import Callable

from mvp.plugins.droneshield_listener.normalize import normalize_payload


class DroneShieldUDPListener:
    def __init__(self, port: int, on_detection: Callable):
        self.port = port
        self.on_detection = on_detection
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self._stop.set()
        try:
            # Nudge by sending an empty packet to unblock recvfrom
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(b"", ("127.0.0.1", self.port))
            sock.close()
        except Exception:
            pass
        self.thread.join(timeout=1.0)

    def _run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", self.port))
        sock.settimeout(0.5)
        try:
            while not self._stop.is_set():
                try:
                    data, _ = sock.recvfrom(65535)
                except socket.timeout:
                    continue
                if not data:
                    continue
                try:
                    text = data.decode("utf-8", errors="ignore").strip()
                    det = normalize_payload(text)
                    if det:
                        self.on_detection(det)
                except Exception:
                    pass
        finally:
            try:
                sock.close()
            except Exception:
                pass


