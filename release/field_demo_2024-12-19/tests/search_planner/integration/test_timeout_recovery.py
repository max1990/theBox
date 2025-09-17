import time

from plugins.search_planner.plugin import SearchPlannerPlugin
from thebox.database import DroneDB
from thebox.event_manager import EventManager


def test_timeout_recovery_does_not_deadlock():
    db = DroneDB()
    em = EventManager(db)
    sp = SearchPlannerPlugin(em)

    # Force tiny analyzer SLA to trigger timeout path
    sp.cfg.timing.analyzer_sla_ms = 1
    # Also very small budgets so the task ends quickly
    sp.cfg.budgets.max_tiles = 1
    sp.cfg.budgets.time_budget_ms = 100

    cue = {"bearing_deg_true": 0.0, "bearing_error_deg": 5.0, "source_type": "vision"}
    sp.on_cue("object.sighting.directional", "payload", cue)
    time.sleep(0.5)
    # Should not hang; returns to IDLE
    assert sp.last_status["state"] == "IDLE"
