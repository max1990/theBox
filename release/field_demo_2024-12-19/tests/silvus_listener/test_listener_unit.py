### `test_listener_unit.py`

from pathlib import Path

from plugins.silvus_listener.parser import parse_lines
from plugins.silvus_listener.plugin import SilvusListenerPlugin


class DummyEventManager:
    def __init__(self):
        self.published = []

    def subscribe(self, *a, **k):
        pass

    def db(self):
        return {}

    def publish(self, *a, **k):
        self.published.append((a, k))


def test_parse_and_normalize():
    FIX = Path(__file__).parent / "fixtures" / "fixture.txt"
    with FIX.open("r", encoding="utf-8") as f:
        recs = list(parse_lines(f))
    assert len(recs) == 1

    plugin = SilvusListenerPlugin("silvus_listener", DummyEventManager())
    outs_before = len(plugin._last_bearings)
    plugin._emit_bearing(recs[0])
    assert len(plugin._last_bearings) == outs_before + 2
    for ev in plugin._last_bearings:
        assert 0.0 <= ev["bearing_deg_true"] < 360.0
        assert "confidence" in ev
