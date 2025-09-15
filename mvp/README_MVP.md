MVP Demo: DroneShield → Normalize → DB → Trakka Slew → Search → Range → SeaCross NMEA

Overview
- Ingests DroneShield fixture lines via UDP
- Normalizes detections and writes to theBox DB (or SQLite shim)
- Slews Trakka (adapter; non-fatal if unavailable)
- Runs a search stub; if verified, bumps confidence 0.75→1.0 and sets range
- Emits SeaCross CLS once, then SGT for follow-ons, with correct checksum
- Single Windows runners to install deps, run tests, then run the demo

Config (env overrides)
- DRONESHIELD_INPUT_FILE=./data/DroneShield_Detections.txt
- DRONESHIELD_UDP_PORT=56000
- REPLAY_INTERVAL_MS=400
- CAMERA_CONNECTED=false
- SEARCH_VERDICT=true
- SEARCH_DURATION_MS=5000
- SEARCH_MAX_MS=10000
- DEFAULT_CONFIDENCE=0.75
- RANGE_KM=2.0
- DB_PATH=thebox_mvp.sqlite
- SEACROSS_HOST=127.0.0.1
- SEACROSS_PORT=2000

Run
1) Use scripts/RUN_ME.bat or scripts/RUN_ME_With_Camera.bat
2) Or via PowerShell equivalents
3) They will create a venv, install deps, run tests, then run the demo


