import threading
from collections.abc import Callable


class SimpleEventBus:
    def __init__(self):
        self._subs: dict[str, list[Callable]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, callback: Callable):
        with self._lock:
            self._subs.setdefault(event_type, []).append(callback)

    def publish(self, event_type: str, payload):
        for cb in list(self._subs.get(event_type, [])):
            try:
                cb(payload)
            except Exception:
                pass
