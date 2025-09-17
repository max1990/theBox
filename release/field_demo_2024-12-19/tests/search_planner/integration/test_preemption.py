import time

from plugins.search_planner.plugin import SearchPlannerPlugin
from thebox.database import DroneDB
from thebox.event_manager import EventManager


def test_preemption_new_cue_interrupts():
    db = DroneDB()
    em = EventManager(db)
    sp = SearchPlannerPlugin(em)

    # Start a long task (radar path will take >= 3 tiles)
    cue1 = {
        "object_id": "preempt-1",
        "bearing_deg_true": 0.0,
        "bearing_error_deg": 5.0,
        "source_type": "radar",
    }
    sp.on_cue("object.sighting.directional", "payload", cue1)
    time.sleep(0.2)

    # Send a high-priority cue (vision), which should preempt
    cue2 = {
        "object_id": "preempt-2",
        "bearing_deg_true": 30.0,
        "bearing_error_deg": 5.0,
        "source_type": "vision",
    }
    sp.on_cue("object.sighting.directional", "payload", cue2)

    time.sleep(1.0)
    # After completion, state returns to IDLE
    assert sp.last_status["state"] == "IDLE"
