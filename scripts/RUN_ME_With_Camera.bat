@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0.."

set CAMERA_CONNECTED=true
call scripts\RUN_ME.bat

@echo off
setlocal
if not exist .venv ( py -3.11 -m venv .venv )
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
IF EXIST pyproject.toml ( pip install -e . ) ELSE ( pip install pydantic pytest )

set CAMERA_CONNECTED=true
if "%DRONESHIELD_INPUT_FILE%"=="" set DRONESHIELD_INPUT_FILE=.\data\DroneShield_Detections.txt
if "%DRONESHIELD_UDP_PORT%"=="" set DRONESHIELD_UDP_PORT=56000
if "%REPLAY_INTERVAL_MS%"=="" set REPLAY_INTERVAL_MS=400
if "%SEARCH_VERDICT%"=="" set SEARCH_VERDICT=true
if "%SEARCH_DURATION_MS%"=="" set SEARCH_DURATION_MS=5000
if "%SEARCH_MAX_MS%"=="" set SEARCH_MAX_MS=10000
if "%RANGE_KM%"=="" set RANGE_KM=2.0
if "%SEACROSS_HOST%"=="" set SEACROSS_HOST=127.0.0.1
if "%SEACROSS_PORT%"=="" set SEACROSS_PORT=2000

pytest -q || exit /b 2
python .\scripts\run_mvp_demo.py
exit /b %ERRORLEVEL%
