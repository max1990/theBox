import threading
from contextlib import contextmanager


class RWLock:
    def __init__(self):
        self._lock = threading.Lock()
        self._read_ready = threading.Condition(self._lock)
        self._readers = 0

    @contextmanager
    def rlock(self):
        with self._lock:
            self._readers += 1
        try:
            yield
        finally:
            with self._lock:
                self._readers -= 1
                if not self._readers:
                    self._read_ready.notify_all()

    @contextmanager
    def wlock(self):
        with self._lock:
            while self._readers > 0:
                self._read_ready.wait()
            yield


class DroneDB:
    def __init__(self):
        self._db = {}
        self._lock = RWLock()

    def get(self, key):
        with self._lock.rlock():
            keys = key.split(".")
            value = self._db
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return None
            return value

    def set(self, key, value):
        with self._lock.wlock():
            keys = key.split(".")
            data = self._db
            for k in keys[:-1]:
                if k not in data or not isinstance(data[k], dict):
                    data[k] = {}
                data = data[k]
            data[keys[-1]] = value

    def delete(self, key):
        with self._lock.wlock():
            keys = key.split(".")
            data = self._db
            for k in keys[:-1]:
                if k not in data or not isinstance(data[k], dict):
                    return
                data = data[k]
            if keys[-1] in data:
                del data[keys[-1]]
