"""
Default configuration for the Search Planner plugin.

These values are intentionally conservative and written in plain English so
non-coders can read and tune them. All durations are in milliseconds.

Angles are relative to bow = 0° (positive to starboard, negative to port).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Timing:
    settle_ms: int = (
        50  # time to let optics/radar settle after a slew (short for tests)
    )
    dwell_ms: int = 150  # time to dwell/capture for analyzer (short for tests)
    analyzer_sla_ms: int = 300  # hard timeout waiting for analyzer verdict


@dataclass
class Budgets:
    time_budget_ms: int = 4000  # total wall-clock budget for a task
    max_tiles: int = 12  # safety cap on number of tiles executed


@dataclass
class PatternParams:
    # Horizon-first ladder around the cue bearing
    default_pattern: str = "HorizonLadder"  # also supports "AzSpiral" (simple)
    step_az_deg: float = 2.0  # azimuth step size
    span_az_deg: float = 10.0  # total span on each side (±)
    ladder_elevations_deg: list[float] = field(default_factory=lambda: [0.0, 1.0, 2.5])


@dataclass
class CapabilityBounds:
    # What knobs are allowed for each modality and their min/max bounds.
    # Adapters must still clamp the final values.
    vision: dict[str, Any] = field(
        default_factory=lambda: {
            "allowed_knobs": ["zoom"],
            "bounds": {"zoom": {"min": 1.0, "max": 30.0}},
        }
    )
    radar: dict[str, Any] = field(
        default_factory=lambda: {
            "allowed_knobs": ["power", "gain", "clutter"],
            "bounds": {
                "power": {"min": 0.1, "max": 1.0},
                "gain": {"min": 0.1, "max": 1.0},
                "clutter": {"min": 0.0, "max": 1.0},
            },
        }
    )


@dataclass
class Artifacts:
    # Where simulators write images/heatmaps for human review.
    artifact_dir: str = "data"


@dataclass
class PlannerConfig:
    timing: Timing = field(default_factory=Timing)
    budgets: Budgets = field(default_factory=Budgets)
    pattern: PatternParams = field(default_factory=PatternParams)
    capabilities: CapabilityBounds = field(default_factory=CapabilityBounds)
    artifacts: Artifacts = field(default_factory=Artifacts)


DEFAULT_CONFIG = PlannerConfig()
