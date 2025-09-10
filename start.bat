@echo off
setlocal enableextensions enabledelayedexpansion

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
  echo Python 3 is not installed.
  exit /b 1
)

where pip >nul 2>nul
if %ERRORLEVEL% neq 0 (
  echo pip is not installed.
  exit /b 1
)

if not exist venv-win (
  echo Creating virtual environment...
  python -m venv venv-win
)

call venv-win\Scripts\activate.bat

echo Installing requirements...
pip install -r requirements.txt

echo Starting The Box...
python app.py %*

echo Deactivating venv...
call venv-win\Scripts\deactivate.bat
