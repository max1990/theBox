# Search Planner — Test Plan

**Purpose:** Ensure the Search Planner behaves per design across unit and integration scopes, with emphasis on (1) strict waiting for analyzer results, (2) budgets/guardrails, (3) correct event payloads, (4) preemption, and (5) optional learning telemetry.

**How to run:**
```bash
pytest -q tests/search_planner
# with coverage:
pytest --cov=plugins/search_planner --cov-report=term-missing
```

**Fixtures (in `tests/search_planner/conftest.py`):**

* `mock_event_bus()` — in-memory pub/sub
* `mock_vision_adapter()`, `mock_radar_adapter()` — respect capability bounds
* `mock_analyzer(delay_ms, script)` — returns `{is_true, score, meta, artifact_path?}`


## Unit Tests — `tests/search_planner/unit/`

**SP-UNIT-01: Horizon ladder tile generation**

* **Goal:** Verify azimuth span, elevation ladder, and wrap to \[-180, 180].
* **Given:** cue 10° ± 5°, step\_az=2°, span\_az=8°, ladder=\[0.5, 1.5, 3.0]
* **Then:** az ∈ \[2°, 18°] by 2°, for each elevation; all wrapped; count matches.

**SP-UNIT-02: Time/Tile budgets respected**

* **Goal:** Do not exceed `max_tiles` nor `time_budget_ms`.
* **Given:** max\_tiles=3, time\_budget\_ms=200
* **When:** adapter always returns false after fixed delay
* **Then:** executed tiles ≤ 3 and/or total time ≤ 200 ms.

**SP-UNIT-03: Immediate halt on first TRUE**

* **Goal:** Stop search as soon as a true decision arrives.
* **Given:** analyzer false for tile1, true for tile2
* **Then:** planner stops after tile2; time\_to\_first\_true\_ms is set.

**SP-UNIT-04: Capability-gated knobs**

* **Goal:** Only set knobs allowed by the modality.
* **Given:** vision caps(zoom=True), radar caps(power/gain/clutter=True)
* **Then:** vision tiles contain `zoom` only; radar tiles contain `power/gain/clutter` only; others absent.

**SP-UNIT-05: Tile timeout handling**

* **Goal:** Analyzer SLA enforced; no hangs.
* **Given:** analyzer never responds
* **Then:** timeout counted; planner REPLANs or fails per policy; process remains responsive.

**SP-UNIT-06: State transitions (happy path)**

* **Goal:** Verify canonical path on early hit.
* **Then:** IDLE → PLANNING → EXECUTING\_TILE → AWAITING\_ANALYSIS → DONE → IDLE

**SP-UNIT-07: State transitions (exhaustion)**

* **Goal:** Verify path when all tiles are negative.
* **Then:** ends in FAILED → IDLE; no publish occurred.

**SP-UNIT-08: Preemption mid-task**

* **Goal:** New high-priority cue interrupts any active state.
* **Then:** planner cancels current task and restarts PLANNING with new cue; no duplicate publish.

**SP-UNIT-09: Publish payload shape**

* **Goal:** Outbound event fields match schema exactly.
* **Then:** `object.sighting.relative` includes bearing, distance (or `range_is_synthetic` + method), confidence (0–100), errors; keys/types asserted.

**SP-UNIT-10: Negative information update**

* **Goal:** Belief map reduces mass for searched tiles.
* **Then:** monotonic drop for the tile region after a false result.


## Integration Tests — `tests/search_planner/integration/`

**SP-INT-01: End-to-end (vision)**

* **Given:** MockVisionAdapter + MockVisionAnalyzer (writes `artifact.jpg`)
* **When:** cue at 0°, analyzer true on second tile
* **Then:** DONE; artifact path recorded; publishes `object.sighting.relative`.

**SP-INT-02: End-to-end (radar)**

* **Given:** MockRadarAdapter + MockRadarAnalyzer (returns SNR + optional `heatmap.png`)
* **When:** false, false, then true with SNR > threshold
* **Then:** DONE; metadata present; heatmap linked if provided.

**SP-INT-03: UI status endpoint**

* **Given:** Flask blueprint running
* **When:** GET `/search_planner/status`
* **Then:** JSON shows current state, last tile, counters; HTML displays thumbnail if artifact exists.

**SP-INT-04: Preemption**

* **When:** a higher-priority cue arrives during AWAITING\_ANALYSIS
* **Then:** current task stops; new task starts; no duplicate publishes.

**SP-INT-05: Timeout recovery**

* **Given:** SLA=800 ms; analyzer stalls
* **Then:** timeout logged; REPLAN once; continues; never deadlocks.

**SP-INT-06: Knob bounds enforcement**

* **Given:** radar bounds power∈\[0.3,0.9], gain∈\[0.2,0.8]
* **When:** planner proposes out-of-bounds
* **Then:** adapter clamps and logs warning (not error).

**SP-INT-07: Learning (shadow) telemetry**

* **Given:** shadow bandit enabled
* **Then:** a row per tile is logged with context, baseline arm, recommended arm, reward, outcome.



## Coverage Goals

* ≥95% branch coverage for scheduler/state transitions.
* 100% of publish paths (true, false, timeout, preemption) executed at least once.
* Event schema tests are byte-for-byte on keys and types.



## Traceability (Design ↔ Tests)

| Design Requirement | Unit Tests       | Integration Tests |
| ------------------ | ---------------- | ----------------- |
| Waits on analyzer  | SP-UNIT-03/05/06 | SP-INT-01/02/05   |
| Budgets enforced   | SP-UNIT-02       | SP-INT-01/02      |
| Capability guards  | SP-UNIT-04       | SP-INT-06         |
| Preemption         | SP-UNIT-08       | SP-INT-04         |
| Correct publish    | SP-UNIT-09       | SP-INT-01/02      |
| Negative updates   | SP-UNIT-10       | —                 |
| Timeouts           | SP-UNIT-05       | SP-INT-05         |
| Learning telemetry | —                | SP-INT-07         |

