import socket
import time
from pathlib import Path
import os, sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from plugins.silvus_listener.plugin import SilvusListenerPlugin
from plugins.silvus_listener.live_udp_client import SilvusUDPClient


class DummyEventManager:
    """Minimal shim so the plugin can call publish()."""
    def __init__(self):
        self.published = []

    def subscribe(self, *a, **k):
        pass

    def db(self):
        return {}

    def publish(self, *a, **k):
        # Some hosts call publish on event_manager; our plugin calls self.publish(),
        # so this may not get hit. Keeping here for completeness.
        self.published.append((a, k))


def _get_free_udp_port() -> int:
    """Ask the OS for a free UDP port on localhost."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.mark.timeout(5)
def test_udp_text_path_end_to_end():
    """
    End-to-end smoke test for live UDP (text mode):
      - Start SilvusUDPClient bound to 127.0.0.1:<freeport>
      - Send a header line (with heading) and a data line (with two AoAs)
      - Expect the plugin to emit TWO object.sighting.directional events
        (one per lobe), appended to _last_bearings
    """
    # Set up plugin (no replay)
    plugin = SilvusListenerPlugin("silvus_listener", DummyEventManager())

    # Start live UDP client with plugin callback
    host = "127.0.0.1"
    port = _get_free_udp_port()
    client = SilvusUDPClient(
        host=host,
        port=port,
        mode="text",
        on_record=plugin._emit_bearing,  # direct callback into plugin
        decoder=None,
    )
    client.start()

    try:
        # Build a single UDP payload containing both lines (header then data)
        # Header line provides heading = 100.0 deg TRUE (as Silvus indicated)
        header = "[172.16.0.46]  Lat/Lon : (36.6,-121.8), Heading (deg): 100.0\n"
        # Data line: timestamp (µs), power, fc MHz, bw MHz, [aoa1, aoa2]
        data =   "[172.16.0.46:1749599078856027] -70.0, 2462.0, 20.0, [15.0, 195.0]\n"
        payload = (header + data).encode("utf-8")

        # Send to the client's bound address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(payload, (host, port))
        s.close()

        # Wait briefly for processing; poll the plugin's ring buffer
        deadline = time.time() + 2.0  # up to 2 seconds
        start_len = len(plugin._last_bearings)
        expected_total = start_len + 2  # two lobes → two bearings

        while time.time() < deadline and len(plugin._last_bearings) < expected_total:
            time.sleep(0.02)

        # Assertions
        assert len(plugin._last_bearings) >= expected_total, (
            f"Expected at least {expected_total} bearings, "
            f"got {len(plugin._last_bearings)}"
        )
        # Validate structure/range
        for ev in list(plugin._last_bearings)[-2:]:
            assert 0.0 <= ev["bearing_deg_true"] < 360.0
            assert isinstance(ev["freq_mhz"], (int, float))
            assert isinstance(ev["bearing_error_deg"], (int, float))
            assert isinstance(ev["confidence"], int)

    finally:
        client.stop()
