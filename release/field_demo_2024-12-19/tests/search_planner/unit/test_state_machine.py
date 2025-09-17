import time

from plugins.search_planner.plugin import SearchPlannerPlugin
from thebox.database import DroneDB
from thebox.event_manager import EventManager


def test_state_transitions_happy_path():
    db = DroneDB()
    em = EventManager(db)
    sp = SearchPlannerPlugin(em)
    cue = {"bearing_deg_true": 0.0, "bearing_error_deg": 5.0, "source_type": "vision"}
    sp.on_cue("object.sighting.directional", "payload", cue)
    time.sleep(1.0)
    # We expect DONE then IDLE final
    assert sp.last_status["state"] == "IDLE"


def test_state_transitions_exhaustion():
    db = DroneDB()
    em = EventManager(db)
    sp = SearchPlannerPlugin(em)
    # Force radar path which returns true only after 3rd tile; limit to 2 tiles so it fails
    sp.cfg.budgets.max_tiles = 2
    cue = {"bearing_deg_true": 0.0, "bearing_error_deg": 5.0, "source_type": "radar"}
    sp.on_cue("object.sighting.directional", "payload", cue)
    time.sleep(1.0)
    # Expect FAILED then IDLE final
    assert sp.last_status["state"] == "IDLE"
