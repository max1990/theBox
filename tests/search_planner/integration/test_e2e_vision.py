import time
from thebox.database import DroneDB
from thebox.event_manager import EventManager
from plugins.search_planner.plugin import SearchPlannerPlugin


def test_e2e_vision_true_on_second_tile():
    db = DroneDB()
    em = EventManager(db)
    sp = SearchPlannerPlugin(em)

    captured = {}

    class Cap:
        def __init__(self, owner):
            self.__self__ = owner
        def __call__(self, event_type, path, value):
            if event_type == "object.sighting.relative" and path == "payload":
                captured.update(value)
            return False

    em.subscribe("object.sighting.relative", "payload", Cap(sp), 0)

    cue = {"object_id": "e2e-vision", "bearing_deg_true": 0.0, "bearing_error_deg": 5.0, "source_type": "vision"}
    sp.on_cue("object.sighting.directional", "payload", cue)
    time.sleep(1.0)

    assert captured.get("object_id") == "e2e-vision"
    assert "bearing_deg_true" in captured
    # Vision sim writes jpg on success
    assert sp.last_status.get("artifact_path", "").endswith("artifact.jpg")

