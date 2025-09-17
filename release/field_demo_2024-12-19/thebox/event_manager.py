import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError


class EventManager:
    def __init__(self, db):
        self.db = db
        self.subscriptions = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.event_history = []

    def subscribe(self, event_type, field, callback, priority):
        if event_type not in self.subscriptions:
            self.subscriptions[event_type] = []
        self.subscriptions[event_type].append(
            {"field": field, "callback": callback, "priority": priority}
        )
        self.subscriptions[event_type].sort(key=lambda x: x["priority"], reverse=True)

    def publish(self, event_type, data, publisher_name="system", store_in_db=True):
        notified_plugins_per_path = {}
        terminated_paths = set()

        if event_type in self.subscriptions:
            for sub in self.subscriptions[event_type]:
                subscriber_name = sub["callback"].__self__.name
                if subscriber_name == publisher_name:
                    continue

                for path, value in data.items():
                    if path in terminated_paths:
                        continue

                    if path.startswith(sub["field"]):
                        if path not in notified_plugins_per_path:
                            notified_plugins_per_path[path] = []
                        notified_plugins_per_path[path].append(subscriber_name)

                        future = self.executor.submit(
                            sub["callback"], event_type, path, value
                        )
                        try:
                            terminate = future.result(timeout=5)
                            if terminate:
                                terminated_paths.add(path)
                        except TimeoutError:
                            print(
                                f"Plugin {subscriber_name} timed out on event {event_type} for path {path}"
                            )
                            terminated_paths.add(path)

        updated_paths = {p: v for p, v in data.items() if p not in terminated_paths}

        if store_in_db:
            for path, value in updated_paths.items():
                if value is None:
                    self.db.delete(path)
                else:
                    self.db.set(path, value)

        all_notified = sorted(
            list(
                set(
                    p
                    for path_plugins in notified_plugins_per_path.values()
                    for p in path_plugins
                )
            )
        )
        was_any_terminated = bool(terminated_paths)

        self.log_event(
            event_type, data, publisher_name, all_notified, was_any_terminated
        )
        return len(terminated_paths) == len(data)

    def log_event(self, event_type, data, publisher_name, notified_plugins, terminated):
        self.event_history.append(
            {
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "event_type": event_type,
                "data": data,
                "publisher": publisher_name,
                "notified_plugins": notified_plugins,
                "terminated": terminated,
            }
        )

    def get_event_history(self):
        return self.event_history
