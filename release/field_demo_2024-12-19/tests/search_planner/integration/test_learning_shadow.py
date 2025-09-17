import time

from plugins.search_planner.plugin import SearchPlannerPlugin
from thebox.database import DroneDB
from thebox.event_manager import EventManager


def test_learning_shadow_runs():
    db = DroneDB()
    em = EventManager(db)
    sp = SearchPlannerPlugin(em)

    cue = {"bearing_deg_true": 0.0, "bearing_error_deg": 5.0, "source_type": "vision"}
    sp.on_cue("object.sighting.directional", "payload", cue)
    time.sleep(0.8)
    # Nothing to assert beyond no exceptions and normal completion back to IDLE
    assert sp.last_status["state"] == "IDLE"
