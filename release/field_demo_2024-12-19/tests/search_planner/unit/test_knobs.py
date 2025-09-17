from plugins.search_planner.plugin import MockRadarAdapter, MockVisionAdapter


def test_vision_knobs_clamped():
    v = MockVisionAdapter({"zoom": {"min": 1.0, "max": 10.0}})
    out = v.clamp_params({"zoom": 50.0, "gain": 1.0})
    assert set(out.keys()) == {"zoom"}
    assert out["zoom"] == 10.0


def test_radar_knobs_clamped():
    r = MockRadarAdapter(
        {"power": {"min": 0.3, "max": 0.9}, "gain": {"min": 0.2, "max": 0.8}}
    )
    out = r.clamp_params({"power": 1.0, "gain": 0.1, "clutter": 1.2, "zoom": 5.0})
    assert set(out.keys()) == {"power", "gain", "clutter"}
    assert out["power"] == 0.9
    assert out["gain"] == 0.2
    # clutter bound defaults to 0..1
    assert out["clutter"] == 1.0
