import threading
import time
from typing import Callable

from mvp.schemas import CameraCommand


class TrakkaAdapter:
    def __init__(self, camera_connected: bool, on_slew_complete: Callable[[str], None]):
        self.camera_connected = camera_connected
        self.on_slew_complete = on_slew_complete

    def slew(self, bearing_deg: float, track_id: str):
        # Prefer real plugin if available. For MVP, just simulate success quickly.
        cmd = CameraCommand(action="slew", bearing_deg=bearing_deg, track_id=track_id)
        # Non-blocking simulation
        threading.Thread(target=self._simulate_slew, args=(cmd,), daemon=True).start()

    def _simulate_slew(self, cmd: CameraCommand):
        # Simulate network send and camera slew latency
        time.sleep(0.1)
        try:
            self.on_slew_complete(str(cmd.track_id))
        except Exception:
            pass


