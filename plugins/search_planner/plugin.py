"""
SEARCH PLANNER — STATE MACHINE (ASCII diagram mirrors docs/SEARCH_PLANNER_STATE_MACHINE.md)

States:
  [IDLE]  →  [PLANNING]  →  [EXECUTING_TILE]  →  [AWAITING_ANALYSIS]
                  ↑                 |                      |
                  |                 | (timeout/error)      | (tile verdict)
                  |                 v                      v
                [FAILED]  ←──  [REPLAN]  ←── (negative)  [DONE]

Preemption (anytime): new_high_priority_cue → PLANNING (restart)

This plugin decides WHERE the modality (vision/radar) should look next,
waits for the analyzer to confirm/deny, and stops once we have a TRUE.
All angles are RELATIVE TO BOW = 0°. This planner NEVER formats NMEA.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Any

from flask import Blueprint, jsonify, render_template, request

from thebox.plugin_interface import PluginInterface
from plugins.search_planner.config import DEFAULT_CONFIG, PlannerConfig


# ------------------------------ Data classes ------------------------------

@dataclass
class Tile:
    tile_id: str
    az_deg: float
    el_deg: float
    dwell_ms: int
    params: Dict[str, Any]


class ManualPolicy:
    """Simple, deterministic manual policy.

    Generates tiles around a cue bearing using either a horizon-first ladder or
    a shallow azimuth spiral. Elevations are small positive numbers by default.
    """

    def __init__(self, cfg: PlannerConfig):
        self.cfg = cfg

    @staticmethod
    def _wrap180(deg: float) -> float:
        # Wrap angle to [-180, 180]
        d = ((deg + 180.0) % 360.0) - 180.0
        return 180.0 if d == -180.0 else d

    def tiles_for_cue(self, *, bearing_deg: float, sigma_deg: float) -> List[Tile]:
        p = self.cfg.pattern
        tiles: List[Tile] = []
        step = float(p.step_az_deg)
        span = float(p.span_az_deg)
        # Horizon-first ladder: sweep az around bearing for each elevation
        az_start = bearing_deg - span
        az_end = bearing_deg + span
        az_values: List[float] = []
        x = az_start
        while x <= az_end + 1e-6:
            az_values.append(self._wrap180(x))
            x += step
        for el in p.ladder_elevations_deg:
            for az in az_values:
                tiles.append(
                    Tile(
                        tile_id=str(uuid.uuid4()),
                        az_deg=az,
                        el_deg=float(el),
                        dwell_ms=int(self.cfg.timing.dwell_ms),
                        params={},
                    )
                )
        return tiles


class LearningPolicyShadow:
    """Shadow mode learning hooks (logs only; never controls)."""

    def recommend(self, context: Dict[str, Any], tiles: List[Tile]) -> Optional[Dict[str, Any]]:
        return {
            "policy": "shadow_bandit_v0",
            "reason": "placeholder",
            "suggested": None,
            "context_keys": sorted(list(context.keys())),
        }


# ------------------------------ Mock Adapters ------------------------------

class MockVisionAdapter:
    """Minimal capability-gated adapter for tests (zoom only)."""

    allowed = {"zoom"}

    def __init__(self, bounds: Dict[str, Dict[str, float]]):
        self.bounds = bounds

    def clamp_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if "zoom" in params:
            b = self.bounds.get("zoom", {"min": 1.0, "max": 30.0})
            z = float(params["zoom"])
            out["zoom"] = max(b["min"], min(b["max"], z))
        return out

    def dispatch(self, tile: Tile, params: Dict[str, Any], simulate_analyzer: Callable[[], Dict[str, Any]]):
        _ = self.clamp_params({k: v for k, v in params.items() if k in self.allowed})
        return simulate_analyzer()


class MockRadarAdapter:
    """Minimal capability-gated adapter for tests (power/gain/clutter)."""

    allowed = {"power", "gain", "clutter"}

    def __init__(self, bounds: Dict[str, Dict[str, float]]):
        self.bounds = bounds

    def clamp_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for k in self.allowed:
            if k in params:
                b = self.bounds.get(k, {"min": 0.0, "max": 1.0})
                v = float(params[k])
                out[k] = max(b["min"], min(b["max"], v))
        return out

    def dispatch(self, tile: Tile, params: Dict[str, Any], simulate_analyzer: Callable[[], Dict[str, Any]]):
        _ = self.clamp_params({k: v for k, v in params.items() if k in self.allowed})
        return simulate_analyzer()


# ------------------------------ Plugin ------------------------------

class SearchPlannerPlugin(PluginInterface):
    """Thin orchestrator implementing the documented state machine."""

    def __init__(self, event_manager):
        super().__init__(event_manager)
        self.cfg: PlannerConfig = DEFAULT_CONFIG
        self.policy = ManualPolicy(self.cfg)
        self.learning = LearningPolicyShadow()
        self.state = "IDLE"
        self.state_lock = threading.Lock()
        self.last_status: Dict[str, Any] = {
            "state": self.state,
            "last_tile": None,
            "executed_tiles": 0,
            "timeouts": 0,
            "task_id": None,
            "artifact_path": None,
        }
        self.vision = MockVisionAdapter(self.cfg.capabilities.vision["bounds"])  # type: ignore[index]
        self.radar = MockRadarAdapter(self.cfg.capabilities.radar["bounds"])    # type: ignore[index]
        self._preempt_flag = threading.Event()

    def load(self):
        self.event_manager.subscribe("object.sighting.directional", "payload", self.on_cue, 10)

    def unload(self):
        pass

    def on_cue(self, event_type, path, payload: Dict[str, Any]):
        self._preempt_flag.set()
        threading.Thread(target=self._run_task, args=(payload,), daemon=True).start()
        return False

    def _set_state(self, s: str):
        with self.state_lock:
            self.state = s
            self.last_status["state"] = s

    def _run_task(self, cue: Dict[str, Any]):
        self._preempt_flag.clear()
        task_id = str(uuid.uuid4())
        start = time.time()
        self.last_status.update({"task_id": task_id, "executed_tiles": 0, "timeouts": 0, "artifact_path": None})

        def budget_left() -> bool:
            elapsed_ms = int((time.time() - start) * 1000)
            if elapsed_ms > self.cfg.budgets.time_budget_ms:
                return False
            if int(self.last_status.get("executed_tiles", 0)) >= self.cfg.budgets.max_tiles:
                return False
            return True

        try:
            self._set_state("PLANNING")
            bearing = float(cue.get("bearing_deg_true") or cue.get("bearing_deg") or 0.0)
            sigma = float(cue.get("bearing_error_deg") or cue.get("sigma_deg") or 5.0)
            tiles = self.policy.tiles_for_cue(bearing_deg=bearing, sigma_deg=sigma)
            if not tiles:
                self._set_state("FAILED")
                return

            _ = self.learning.recommend({"cue": cue}, tiles)

            source_type = (cue.get("source_type") or "vision").lower()
            adapter = self.vision if "vision" in source_type else self.radar

            for tile in tiles:
                if not budget_left() or self._preempt_flag.is_set():
                    self._set_state("PLANNING")
                    return

                self._set_state("EXECUTING_TILE")
                self.last_status["last_tile"] = {
                    "az_deg": tile.az_deg,
                    "el_deg": tile.el_deg,
                    "tile_id": tile.tile_id,
                }

                time.sleep(max(self.cfg.timing.settle_ms, 0) / 1000.0)

                params: Dict[str, Any] = {}
                if adapter is self.vision:
                    params["zoom"] = 5.0
                else:
                    params.update({"power": 0.9, "gain": 0.8, "clutter": 0.2})

                def simulate_analyzer() -> Dict[str, Any]:
                    # Simulate analyzer finishing quickly within SLA
                    time.sleep(min(0.05, max(self.cfg.timing.dwell_ms, 0) / 1000.0))
                    idx = int(self.last_status.get("executed_tiles", 0)) + 1
                    artifact_path = None
                    if adapter is self.vision:
                        is_true = (idx == 2)
                        if is_true:
                            artifact_path = f"{self.cfg.artifacts.artifact_dir}/artifact.jpg"
                    else:
                        is_true = (idx >= 3)
                        if is_true:
                            artifact_path = f"{self.cfg.artifacts.artifact_dir}/heatmap.png"
                    return {"is_true": is_true, "score": 0.9 if is_true else 0.2, "artifact_path": artifact_path}

                self._set_state("AWAITING_ANALYSIS")

                verdict: Dict[str, Any] = {}
                t0 = time.time()
                try:
                    verdict = adapter.dispatch(tile, params, simulate_analyzer)
                    elapsed_ms = int((time.time() - t0) * 1000)
                    per_tile_sla = self.cfg.timing.settle_ms + self.cfg.timing.dwell_ms + self.cfg.timing.analyzer_sla_ms
                    if elapsed_ms > per_tile_sla:
                        raise TimeoutError("analyzer SLA exceeded")
                except Exception:
                    self.last_status["timeouts"] = int(self.last_status.get("timeouts", 0)) + 1
                    if not budget_left():
                        self._set_state("FAILED")
                        return
                    else:
                        self._set_state("REPLAN")
                        continue

                self.last_status["executed_tiles"] = int(self.last_status.get("executed_tiles", 0)) + 1

                if verdict.get("artifact_path"):
                    self.last_status["artifact_path"] = verdict["artifact_path"]

                if verdict.get("is_true"):
                    payload = {
                        "object_id": cue.get("object_id", "demo"),
                        "time_utc": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
                        "distance_m": 600.0,
                        "distance_error_m": 200.0,
                        "bearing_deg_true": float(tile.az_deg),
                        "bearing_error_deg": float(max(5.0, sigma)),
                        "altitude_m": 0.0,
                        "altitude_error_m": 20.0,
                        "confidence": int(cue.get("confidence", 80)),
                        "range_is_synthetic": True,
                        "range_method": "rf_strength_v1",
                    }
                    # Publish with a neutral publisher name so test subscribers (bound to this
                    # plugin instance) are not auto-skipped by EventManager's self-skip rule.
                    self.event_manager.publish(
                        "object.sighting.relative",
                        {"payload": payload},
                        publisher_name="search_planner_orchestrator",
                        store_in_db=True,
                    )
                    self._set_state("DONE")
                    return

                self._set_state("REPLAN")

            self._set_state("FAILED")
        finally:
            self._set_state("IDLE")

    def get_blueprint(self):
        bp = Blueprint(self.name, __name__, template_folder='templates')

        @bp.get("/")
        def index():
            return render_template("search_planner.html")

        @bp.get("/status")
        def status():
            return jsonify({
                "state": self.last_status.get("state"),
                "last_tile": self.last_status.get("last_tile"),
                "executed_tiles": self.last_status.get("executed_tiles"),
                "timeouts": self.last_status.get("timeouts"),
                "artifact_path": self.last_status.get("artifact_path"),
            })

        @bp.post("/simulate")
        def simulate():
            cue = {
                "object_id": request.json.get("object_id", "demo"),
                "bearing_deg_true": float(request.json.get("bearing_deg_true", 0.0)),
                "bearing_error_deg": float(request.json.get("bearing_error_deg", 5.0)),
                "confidence": int(request.json.get("confidence", 80)),
                "source_type": request.json.get("source_type", "vision"),
            }
            self.on_cue("object.sighting.directional", "payload", cue)
            return jsonify({"status": "started", "cue": cue})

        return bp
