Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')

if (-not (Test-Path .venv)) { py -3 -m venv .venv }
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
if (Test-Path pyproject.toml) { pip install -e . } else { pip install pydantic pytest }

if (-not $env:DRONESHIELD_INPUT_FILE) { $env:DRONESHIELD_INPUT_FILE = './data/DroneShield_Detections.txt' }
if (-not $env:DRONESHIELD_UDP_PORT) { $env:DRONESHIELD_UDP_PORT = '56000' }
if (-not $env:REPLAY_INTERVAL_MS) { $env:REPLAY_INTERVAL_MS = '400' }
if (-not $env:CAMERA_CONNECTED) { $env:CAMERA_CONNECTED = 'false' }
if (-not $env:SEARCH_VERDICT) { $env:SEARCH_VERDICT = 'true' }
if (-not $env:SEARCH_DURATION_MS) { $env:SEARCH_DURATION_MS = '5000' }
if (-not $env:SEARCH_MAX_MS) { $env:SEARCH_MAX_MS = '10000' }
if (-not $env:DEFAULT_CONFIDENCE) { $env:DEFAULT_CONFIDENCE = '0.75' }
if (-not $env:RANGE_KM) { $env:RANGE_KM = '2.0' }
if (-not $env:DB_PATH) { $env:DB_PATH = 'thebox_mvp.sqlite' }
if (-not $env:SEACROSS_HOST) { $env:SEACROSS_HOST = '127.0.0.1' }
if (-not $env:SEACROSS_PORT) { $env:SEACROSS_PORT = '2000' }

pytest -q
python -m scripts.run_mvp

deactivate

if (!(Test-Path .venv)) { py -3.11 -m venv .venv }
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
if (Test-Path .\pyproject.toml) { pip install -e . } else { pip install pydantic pytest }

if (-not $env:DRONESHIELD_INPUT_FILE) { $env:DRONESHIELD_INPUT_FILE = ".\data\DroneShield_Detections.txt" }
if (-not $env:DRONESHIELD_UDP_PORT)   { $env:DRONESHIELD_UDP_PORT   = "56000" }
if (-not $env:REPLAY_INTERVAL_MS)     { $env:REPLAY_INTERVAL_MS     = "400" }
if (-not $env:CAMERA_CONNECTED)       { $env:CAMERA_CONNECTED       = "false" }
if (-not $env:SEARCH_VERDICT)         { $env:SEARCH_VERDICT         = "true" }
if (-not $env:SEARCH_DURATION_MS)     { $env:SEARCH_DURATION_MS     = "5000" }
if (-not $env:SEARCH_MAX_MS)          { $env:SEARCH_MAX_MS          = "10000" }
if (-not $env:RANGE_KM)               { $env:RANGE_KM               = "2.0" }
if (-not $env:SEACROSS_HOST)          { $env:SEACROSS_HOST          = "127.0.0.1" }
if (-not $env:SEACROSS_PORT)          { $env:SEACROSS_PORT          = "2000" }

pytest -q
if ($LASTEXITCODE -ne 0) { exit 2 }
python .\scripts\run_mvp_demo.py
exit $LASTEXITCODE
