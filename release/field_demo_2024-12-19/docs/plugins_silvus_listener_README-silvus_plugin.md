# Silvus Listener Plugin

**Goal:** minimal “frequency → bearing(s)” integration.

- Parses Silvus AoA outputs
- Combines AoA with **true heading** → `bearing_deg_true`
- Publishes `object.sighting.directional` only (no ranges/CLS/SGT here)

## Conventions & Policy
- AoA units: degrees; values may exceed 360 → wrap to [0, 360)
- Heading: **true** heading (per Silvus)
- Confidence: integer 0–100, default 75
- Error: default `bearing_error_deg = 5.0` (replace with vendor per-detection field when available)
- If heading is missing, **skip emission**

## Files
 ├── init.py
├── config.py
├── bearing.py
├── parser.py
├── live_udp_client.py
├── plugin.py
└── templates/
└── silvus_listener.html

## Usage

### Replay (text log)
- export SILVUS_REPLAY_PATH=tests/silvus_listener/fixtures/fixture.txt

# start the app so the plugin loads, or run tests
- pytest -q tests/silvus_listener

# Live UDP (text mode)
export SILVUS_UDP_HOST=0.0.0.0
export SILVUS_UDP_PORT=50051
export SILVUS_UDP_MODE=text

# start the app so the plugin loads and begins listening
- For protobuf mode, set SILVUS_UDP_MODE=protobuf and provide a real decoder in
- live_udp_client.example_protobuf_decoder once Silvus shares the .proto.

# Emits
{
  "time_utc": "2025-09-10T08:00:00Z",
  "freq_mhz": 2462.0,
  "bearing_deg_true": 135.0,
  "bearing_error_deg": 5.0,
  "confidence": 75
}

NOTE: If heading is missing (no GPS), emission is skipped.

