import os
import tempfile
import asyncio

from plugins.confidence.confidence_plugin import ConfidencePlugin
from plugins.range.range_plugin import RangePlugin
from plugins.vision.vision_plugin import VisionPlugin, VisionConfig


def test_confidence_unit():
    os.environ["CONFIDENCE_BASE"] = "0.75"
    os.environ["CONFIDENCE_TRUE"] = "1.0"
    os.environ["CONFIDENCE_FALSE"] = "0.5"
    c = ConfidencePlugin()
    assert abs(c.initial_score() - 0.75) < 1e-6
    assert abs(c.update_after_vision(0.75, True) - 1.0) < 1e-6
    assert abs(c.update_after_vision(0.75, False) - 0.75) < 1e-6
    assert abs(c.update_after_vision(0.6, False) - 0.6) < 1e-6
    assert abs(c.update_after_vision(0.4, False) - 0.5) < 1e-6


def test_range_modes():
    os.environ["RANGE_MODE"] = "fixed"
    os.environ["RANGE_FIXED_KM"] = "2.0"
    r = RangePlugin()
    assert abs(r.estimate_km({}, None) - 2.0) < 1e-6

    os.environ["RANGE_MODE"] = "rssi"
    os.environ["RANGE_RSSI_REF_DBM"] = "-50"
    os.environ["RANGE_RSSI_REF_KM"] = "2.0"
    r = RangePlugin()
    v = r.estimate_km({"RSSI": -60}, None)
    assert v >= 0.1 and v <= 8.0

    os.environ["RANGE_MODE"] = "hybrid"
    r = RangePlugin()
    v2 = r.estimate_km({"RSSI": -60}, None)
    assert v2 >= 0.1 and v2 <= 8.0


def test_vision_false_then_true(monkeypatch):
    cfg = VisionConfig(verdict_true=False, label="Quad", latency_ms=1, max_ms=10)
    v = VisionPlugin(cfg)

    res = asyncio.run(v.run_verification("t1"))
    assert res.verified is False

    v.cfg.verdict_true = True
    res2 = asyncio.run(v.run_verification("t1"))
    assert res2.verified is True


