import time
from plugins.search_planner.plugin import SearchPlannerPlugin
from plugins.search_planner.config import PlannerConfig
from thebox.event_manager import EventManager
from thebox.database import DroneDB


def test_budgets_respected():
    db = DroneDB()
    em = EventManager(db)
    plugin = SearchPlannerPlugin(em)
    # Tight budgets to force early stop
    plugin.cfg.budgets.max_tiles = 3
    plugin.cfg.budgets.time_budget_ms = 200

    cue = {"bearing_deg_true": 0.0, "bearing_error_deg": 5.0, "source_type": "vision"}
    plugin.on_cue("object.sighting.directional", "payload", cue)

    # Wait a bit for background thread
    time.sleep(0.6)

    assert plugin.last_status["executed_tiles"] <= 3

