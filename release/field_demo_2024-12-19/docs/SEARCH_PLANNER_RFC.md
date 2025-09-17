Awesome—making the searcher its own plugin is the right call. Here’s a crisp plan you can drop into your plugin ecosystem so any modality (vision, radar, acoustic, etc.) can “call” a common search engine while exposing only the knobs that modality is allowed to change.

# What we’re building

A **Search Plugin** that:

* Takes a cue (bearing ± error, context) and **plans/execut es camera/radar “tiles”** (az/el/zoom or radar params) until a downstream **Detector** returns TRUE (or time/budget expires).
* **Waits for the detector** to analyze the current tile before moving on.
* **Adapts per modality** via a Capability Profile (e.g., vision can change zoom; radar can change power/gain/clutter).
* Emits standard **events + artifacts** (e.g., for vision, return a snapshot; for radar, return a detection record and optional heatmap/scope image if available).

# Clean plugin boundary (stable API)

```
SearchPlugin.search(cue: Cue, config: SearchConfig, modality: ModalityAdapter) -> SearchResult
```

## Core data types (stable across modalities)

* `Cue`: bearing\_deg, sigma\_deg, source\_type, confidence, optional priors.
* `SearchConfig`: budgets (time/tiles), PTZ/radar kinematics, pattern & params, bandit toggle, dwell\_ms, settle models, retry limits.
* `CapabilityProfile`: declares what the **modality is allowed** to change (zoom, focus, power, gain, clutter, PRF, etc.) and any bounds.
* `Tile`: the schedulable step (vision: az/el/zoom; radar: az/el + control knobs).
* `Observation`: what the modality returns for that tile (features + optional artifact).
* `Decision`: detector verdict for that observation (true/false + score).
* `SearchResult`: status, time\_to\_first\_true, chosen tiles, winning tile, **artifact(s)** (image for vision, record/PNG for radar if provided).

# Control & waiting rule

* The **Search Plugin owns the schedule** (patterns, sequencing, timeouts).
* The **Modality Adapter executes** the tile and **blocks/awaits** its detector’s analysis for that tile, returning `(Observation, Decision, optional Artifact)`.
* If `Decision.true == True`, the search **halts immediately** and returns results.

# Capability-driven control (what each modality can change)

Examples:

* **Vision** (`Trakka`): az, el, **zoom**, focus mode, exposure; (zoom is crucial).
* **Radar** (`Dspnor`): az, el (if steerable), **power**, **gain**, **sea/land clutter**, **CFAR**, **PRF**, **scan width**.
* **Acoustic** (future): az (beam steer), gain, integration time.

The plugin won’t try to twiddle knobs the adapter hasn’t allowed in its `CapabilityProfile`.

---

# Minimal, production-shaped Python scaffold

> Paste this into Cursor and you’ll get a working skeleton you can extend. It’s synchronous by default; flip to `async` later if you want overlapping operations.

```python
# search_plugin/api.py
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple, Any, Protocol

@dataclass
class Cue:
    bearing_deg: float
    sigma_deg: float
    source_type: str            # "RF" | "Acoustic" | "Radar" | ...
    confidence: float = 0.5
    context: Dict[str, Any] = None  # wind, day/night, ducting, etc.

@dataclass
class CapabilityProfile:
    # What knobs THIS modality allows the searcher to set
    can_set_zoom: bool = False
    can_set_focus: bool = False
    can_set_exposure: bool = False
    can_set_power: bool = False
    can_set_gain: bool = False
    can_set_clutter: bool = False
    # add more as needed; also include bounds per knob if useful
    bounds: Dict[str, Tuple[float, float]] = None

@dataclass
class Tile:
    az_deg: float
    el_deg: float
    dwell_ms: int
    params: Dict[str, Any]       # e.g., {"zoom": "MEDIUM"} or {"power": 0.8, "gain": 0.4}

@dataclass
class Observation:
    # Raw/processed features returned by the modality (blob stats, radar cells, etc.)
    features: Dict[str, Any]
    artifact: Optional[bytes] = None     # e.g., JPEG/PNG for vision, PNG/scope for radar

@dataclass
class Decision:
    is_true: bool
    score: float
    metadata: Dict[str, Any]

@dataclass
class SearchConfig:
    time_budget_ms: int = 15000
    max_tiles: int = 50
    settle_ms: int = 250
    default_pattern: str = "HorizonLadder"  # "AzSpiral" | "RasterBox" | "TwoStage"
    dwell_ms: int = 300
    zoom_ladder: List[str] = None           # e.g., ["WIDE","MEDIUM","NARROW"]
    pattern_params: Dict[str, Any] = None   # step sizes, box sizes, etc.

@dataclass
class SearchResult:
    found: bool
    time_to_first_true_ms: Optional[int]
    tiles_executed: List[Tile]
    winning_tile: Optional[Tile]
    artifact: Optional[bytes]    # Vision: snapshot; Radar: optional scope/heatmap
    decision: Optional[Decision]
    log: List[Dict[str, Any]]    # for bandit/off-policy later

class ModalityAdapter(Protocol):
    @property
    def capabilities(self) -> CapabilityProfile: ...
    def get_state(self) -> Dict[str, Any]: ...
    def execute_tile_and_analyze(self, tile: Tile, config: SearchConfig) -> Tuple[Observation, Decision]:
        """Must BLOCK until detection analysis for this tile is done.
        Return Observation (may include artifact bytes) and Decision."""
        ...
```

### Patterns + scheduler

```python
# search_plugin/patterns.py
from typing import List
from .api import Cue, SearchConfig, Tile

def horizon_ladder(cue: Cue, cfg: SearchConfig) -> List[Tile]:
    # Start near horizon, sweep +/- around cue bearing, then ladder up
    step_az = cfg.pattern_params.get("step_az_deg", 2.0)
    ladder_el = cfg.pattern_params.get("ladder_el_deg", [0.5, 1.5, 3.0])
    span_az = cfg.pattern_params.get("span_az_deg", 8.0)
    dwell = cfg.dwell_ms

    tiles: List[Tile] = []
    for el in ladder_el:
        azs = [cue.bearing_deg + a for a in frange(-span_az, span_az, step_az)]
        for az in azs:
            tiles.append(Tile(az_deg=wrap(az), el_deg=el, dwell_ms=dwell, params={}))
    return tiles

def frange(a,b,step):
    x=a
    while x<=b:
        yield x
        x+=step

def wrap(angle):
    while angle < -180: angle+=360
    while angle > 180: angle-=360
    return angle
```

```python
# search_plugin/scheduler.py
import time
from typing import List, Dict, Any
from .api import Cue, SearchConfig, SearchResult, Tile, ModalityAdapter, Decision
from . import patterns

PATTERN_MAP = {
    "HorizonLadder": patterns.horizon_ladder,
    # "AzSpiral": patterns.az_spiral,
    # "RasterBox": patterns.raster_box,
    # "TwoStage": patterns.two_stage,
}

def build_tiles(cue: Cue, cfg: SearchConfig) -> List[Tile]:
    gen = PATTERN_MAP[cfg.default_pattern]
    tiles = gen(cue, cfg)
    # inject allowed params according to capability
    return tiles

def apply_capabilities(tile: Tile, caps, cfg: SearchConfig, state: Dict[str, Any]) -> Tile:
    params = dict(tile.params)
    if caps.can_set_zoom and cfg.zoom_ladder:
        # crude: start WIDE then MEDIUM later; smarter policies can be learned
        idx = min(1, len(cfg.zoom_ladder)-1)  # MEDIUM if available
        params["zoom"] = cfg.zoom_ladder[idx]
    if caps.can_set_power and "power" not in params:
        params["power"] = 0.8
    if caps.can_set_gain and "gain" not in params:
        params["gain"] = 0.4
    if caps.can_set_clutter and "clutter" not in params:
        params["clutter"] = "sea"
    return Tile(az_deg=tile.az_deg, el_deg=tile.el_deg, dwell_ms=tile.dwell_ms, params=params)

def search(cue: Cue, cfg: SearchConfig, modality: ModalityAdapter) -> SearchResult:
    start = now_ms()
    tiles = build_tiles(cue, cfg)
    executed: List[Tile] = []
    log: List[Dict[str, Any]] = []
    found=False; winning=None; decision=None; artifact=None

    for i, t in enumerate(tiles):
        if i >= cfg.max_tiles or now_ms()-start >= cfg.time_budget_ms:
            break

        state = modality.get_state()
        t2 = apply_capabilities(t, modality.capabilities, cfg, state)

        # settle
        time.sleep(cfg.settle_ms/1000.0)

        obs, dec = modality.execute_tile_and_analyze(t2, cfg)  # blocks until detector is done
        executed.append(t2)
        log.append({"tile": t2, "decision": vars(dec), "t_ms": now_ms()-start})

        if dec.is_true:
            found=True; winning=t2; decision=dec; artifact=obs.artifact
            break

    ttf = now_ms()-start if found else None
    return SearchResult(found=found, time_to_first_true_ms=ttf, tiles_executed=executed,
                        winning_tile=winning, artifact=artifact, decision=decision, log=log)

def now_ms(): return int(time.time()*1000)
```

### Vision adapter (Trakka example)

```python
# adapters/vision_trakka.py
from typing import Tuple
from .search_plugin.api import CapabilityProfile, Tile, Observation, Decision, SearchConfig
from .search_plugin.api import ModalityAdapter

class TrakkaVisionAdapter(ModalityAdapter):
    def __init__(self, controller, detector):
        self._caps = CapabilityProfile(can_set_zoom=True, can_set_focus=True)
        self.controller = controller   # your PTZ/zoom/focus driver
        self.detector = detector       # your vision model service

    @property
    def capabilities(self) -> CapabilityProfile:
        return self._caps

    def get_state(self):
        return self.controller.get_state()

    def execute_tile_and_analyze(self, tile: Tile, cfg: SearchConfig) -> Tuple[Observation, Decision]:
        # move & set zoom
        self.controller.point(tile.az_deg, tile.el_deg)
        if "zoom" in tile.params:
            self.controller.set_zoom(tile.params["zoom"])
        # optional focus/exposure tuning here

        # dwell & capture
        self.controller.wait_for_stabilization()
        frame = self.controller.capture_jpeg(dwell_ms=tile.dwell_ms)  # artifact for “vision”
        verdict = self.detector.infer(frame)  # returns {is_true, score, meta}

        obs = Observation(features={"vision_score": verdict["score"]}, artifact=frame)
        dec = Decision(is_true=verdict["is_true"], score=verdict["score"], metadata=verdict.get("meta", {}))
        return obs, dec
```

### Radar adapter (Dspnor example)

```python
# adapters/radar_dspnor.py
from typing import Tuple
from .search_plugin.api import CapabilityProfile, Tile, Observation, Decision, SearchConfig, ModalityAdapter

class DspnorRadarAdapter(ModalityAdapter):
    def __init__(self, radar_driver, detector):
        self._caps = CapabilityProfile(can_set_power=True, can_set_gain=True, can_set_clutter=True)
        self.radar = radar_driver
        self.detector = detector

    @property
    def capabilities(self) -> CapabilityProfile:
        return self._caps

    def get_state(self):
        return self.radar.get_state()

    def execute_tile_and_analyze(self, tile: Tile, cfg: SearchConfig) -> Tuple[Observation, Decision]:
        # steer and set radar controls as allowed
        self.radar.point(tile.az_deg, tile.el_deg)
        if "power" in tile.params: self.radar.set_power(tile.params["power"])
        if "gain" in tile.params: self.radar.set_gain(tile.params["gain"])
        if "clutter" in tile.params: self.radar.set_clutter(tile.params["clutter"])

        cells, aux = self.radar.collect(dwell_ms=tile.dwell_ms)   # raw/MTI cells + aux data
        verdict = self.detector.infer(cells)  # radar-domain detector

        # Optional artifact: e.g., render a small PNG heatmap (do it inside detector or here)
        artifact = aux.get("heatmap_png") if isinstance(aux, dict) else None

        obs = Observation(features={"radar_snr": verdict["snr"]}, artifact=artifact)
        dec = Decision(is_true=verdict["is_true"], score=verdict["snr"], metadata=verdict.get("meta", {}))
        return obs, dec
```

### CLI wrapper

```python
# cli/search_run.py
import json, argparse
from search_plugin.api import Cue, SearchConfig
from search_plugin.scheduler import search
# from adapters.vision_trakka import TrakkaVisionAdapter
# from adapters.radar_dspnor import DspnorRadarAdapter

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bearing", type=float, required=True)
    ap.add_argument("--sigma", type=float, default=5.0)
    ap.add_argument("--source", type=str, default="RF")
    ap.add_argument("--budget-ms", type=int, default=15000)
    ap.add_argument("--pattern", type=str, default="HorizonLadder")
    args = ap.parse_args()

    cue = Cue(bearing_deg=args.bearing, sigma_deg=args.sigma, source_type=args.source)
    cfg = SearchConfig(time_budget_ms=args.budget_ms, default_pattern=args.pattern,
                       dwell_ms=300, zoom_ladder=["WIDE","MEDIUM","NARROW"],
                       pattern_params={"step_az_deg":2.0,"span_az_deg":8.0,"ladder_el_deg":[0.5,1.5,3.0]})

    # modality = TrakkaVisionAdapter(controller=..., detector=...)
    # OR
    # modality = DspnorRadarAdapter(radar_driver=..., detector=...)

    # Placeholder to show structure only
    raise SystemExit("Wire a real modality adapter and call search(cue, cfg, modality)")

if __name__ == "__main__":
    main()
```

---

## How we satisfy your specific asks

* **Plugin, reusable by anything**: `ModalityAdapter` interface + `CapabilityProfile` makes the searcher agnostic to vision/radar and future sensors.
* **Vision returns a photo**: Vision adapter captures a JPEG during the dwell and returns it as the artifact inside `SearchResult`.
* **Radar return value**: Radar adapter returns a **Decision** and (optionally) a **rendered heatmap/Scope PNG** as artifact; if you don’t want an image, you still get the detection metadata (SNR, range bin, doppler).
* **Wait for detector**: `execute_tile_and_analyze` **blocks** until the detector finishes; the scheduler won’t move the camera/radar until it has the verdict.
* **Per-modality knobs**: Capability-driven `apply_capabilities()` only sets zoom for vision; only sets power/gain/clutter for radar; easy to extend (PRF, CFAR, exposure).

---

## Production next steps (quick wins)

1. Drop this skeleton into your repo; wire `TrakkaVisionAdapter.controller` to your existing PTZ/zoom API and `detector` to whatever gRPC/REST/local model you’re using.
2. Add the other patterns (`AzSpiral`, `RasterBox`, `TwoStage`)—the scaffolding is already there.
3. Add logging (Parquet/JSONL) + a tiny **contextual bandit** that chooses which pattern to run given `Cue.context` (shadow mode first).
4. Implement a **timeout** inside `execute_tile_and_analyze` so a hung detector doesn’t stall the search (return `is_true=False` on timeout and keep going).
5. For RHIBs, keep **zoom hysteresis** and **max slew/sec** in `SearchConfig` and enforce it in the controller to avoid focus/slew thrash.

---