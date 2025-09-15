@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0.."

if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if exist pyproject.toml (
  pip install -e .
) else (
  pip install pydantic pytest
)

set DRONESHIELD_INPUT_FILE=%DRONESHIELD_INPUT_FILE%
if "%DRONESHIELD_INPUT_FILE%"=="" set DRONESHIELD_INPUT_FILE=./data/DroneShield_Detections.txt
if "%DRONESHIELD_UDP_PORT%"=="" set DRONESHIELD_UDP_PORT=56000
if "%REPLAY_INTERVAL_MS%"=="" set REPLAY_INTERVAL_MS=400
if "%CAMERA_CONNECTED%"=="" set CAMERA_CONNECTED=false
if "%SEARCH_VERDICT%"=="" set SEARCH_VERDICT=true
if "%SEARCH_DURATION_MS%"=="" set SEARCH_DURATION_MS=5000
if "%SEARCH_MAX_MS%"=="" set SEARCH_MAX_MS=10000
if "%DEFAULT_CONFIDENCE%"=="" set DEFAULT_CONFIDENCE=0.75
if "%RANGE_KM%"=="" set RANGE_KM=2.0
if "%DB_PATH%"=="" set DB_PATH=thebox_mvp.sqlite
if "%SEACROSS_HOST%"=="" set SEACROSS_HOST=127.0.0.1
if "%SEACROSS_PORT%"=="" set SEACROSS_PORT=2000

pytest -q || goto :eof
python -m scripts.run_mvp

deactivate
exit /b %ERRORLEVEL%

@echo off
setlocal

REM ===== Repo root guard =====
if not exist "%~dp0..\mvp" (
  echo [RUN_ME] Please run this from the repo root (where the mvp/ folder exists).
  echo Example:  scripts\RUN_ME.bat
  exit /b 1
)

REM ===== Python venv =====
if not exist .venv (
  echo [RUN_ME] Creating venv...
  py -3.11 -m venv .venv
)
call .venv\Scripts\activate.bat

echo [RUN_ME] Upgrading pip and installing deps...
python -m pip install --upgrade pip
IF EXIST pyproject.toml (
  pip install -e .
) ELSE (
  pip install pydantic pytest
)

REM ===== Defaults (don’t override if already set in user env) =====
if "%DRONESHIELD_INPUT_FILE%"=="" set DRONESHIELD_INPUT_FILE=.\data\DroneShield_Detections.txt
if "%DRONESHIELD_UDP_PORT%"=="" set DRONESHIELD_UDP_PORT=56000
if "%REPLAY_INTERVAL_MS%"=="" set REPLAY_INTERVAL_MS=400
if "%CAMERA_CONNECTED%"=="" set CAMERA_CONNECTED=false
if "%SEARCH_VERDICT%"=="" set SEARCH_VERDICT=true
if "%SEARCH_DURATION_MS%"=="" set SEARCH_DURATION_MS=5000
if "%SEARCH_MAX_MS%"=="" set SEARCH_MAX_MS=10000
if "%RANGE_KM%"=="" set RANGE_KM=2.0
if "%SEACROSS_HOST%"=="" set SEACROSS_HOST=127.0.0.1
if "%SEACROSS_PORT%"=="" set SEACROSS_PORT=2000

echo [RUN_ME] Running tests...
pytest -q
if errorlevel 1 (
  echo [RUN_ME] Tests failed.
  exit /b 2
)

echo [RUN_ME] Starting MVP demo...
python .\scripts\run_mvp_demo.py
set ERR=%ERRORLEVEL%

if %ERR%==0 (
  echo [RUN_ME] DONE. See mvp_demo.log for details.
) else (
  echo [RUN_ME] Demo exited with code %ERR%.
)
exit /b %ERR%
