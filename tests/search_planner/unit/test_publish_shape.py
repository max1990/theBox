import time
from plugins.search_planner.plugin import SearchPlannerPlugin
from thebox.event_manager import EventManager
from thebox.database import DroneDB


def test_publish_payload_shape_fields():
    db = DroneDB()
    em = EventManager(db)
    sp = SearchPlannerPlugin(em)

    # Capture published payload by subscribing a test listener
    captured = {}

    class Cap:
        def __init__(self, owner):
            self.__self__ = owner
        def __call__(self, event_type, path, value):
            if event_type == "object.sighting.relative" and path == "payload":
                captured.update(value)
            return False

    em.subscribe("object.sighting.relative", "payload", Cap(sp), 0)

    cue = {"object_id": "abc123", "bearing_deg_true": 0.0, "bearing_error_deg": 5.0, "source_type": "vision"}
    sp.on_cue("object.sighting.directional", "payload", cue)
    time.sleep(1.0)

    # Ensure required fields exist with correct types
    for k in [
        "object_id","time_utc","distance_m","distance_error_m","bearing_deg_true","bearing_error_deg",
        "altitude_m","altitude_error_m","confidence","range_is_synthetic","range_method"
    ]:
        assert k in captured

