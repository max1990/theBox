from plugins.search_planner.plugin import ManualPolicy
from plugins.search_planner.config import PlannerConfig


def test_horizon_ladder_tile_generation_wrap():
    cfg = PlannerConfig()
    cfg.pattern.step_az_deg = 2.0
    cfg.pattern.span_az_deg = 8.0
    cfg.pattern.ladder_elevations_deg = [0.5, 1.5, 3.0]
    policy = ManualPolicy(cfg)

    tiles = policy.tiles_for_cue(bearing_deg=10.0, sigma_deg=5.0)

    # Expected az values from 2 to 18 step 2 (wrapped to [-180,180])
    expected_az = [2, 4, 6, 8, 10, 12, 14, 16, 18]
    # For each elevation
    assert len(tiles) == len(expected_az) * len(cfg.pattern.ladder_elevations_deg)
    # Check ranges and wrapping
    for t in tiles:
        assert -180.0 <= t.az_deg <= 180.0
        assert round(t.az_deg) in expected_az
        assert t.el_deg in cfg.pattern.ladder_elevations_deg


