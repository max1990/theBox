import threading
import time
from typing import Callable


class SearchStub:
    def __init__(self, verdict: bool, duration_ms: int, max_ms: int, on_result: Callable[[str, bool], None]):
        self.verdict = verdict
        self.duration_ms = duration_ms
        self.max_ms = max_ms
        self.on_result = on_result

    def run(self, track_id: str):
        threading.Thread(target=self._do_search, args=(track_id,), daemon=True).start()

    def _do_search(self, track_id: str):
        start = time.time()
        # Wait for duration but cap at max
        target = min(self.duration_ms, self.max_ms) / 1000.0
        while time.time() - start < target:
            time.sleep(0.05)
        try:
            self.on_result(track_id, self.verdict)
        except Exception:
            pass


