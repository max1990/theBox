@echo off
setlocal

REM Create venv if missing
if not exist .venv (
  py -3.11 -m venv .venv
)

REM Activate venv
call .venv\Scripts\activate.bat

REM Upgrade pip + install deps (idempotent)
python -m pip install --upgrade pip
IF EXIST pyproject.toml (
  pip install -e .
) ELSE (
  pip install pydantic pytest
)

REM Run tests (optional)
pytest -q || goto :eof

REM Run the demo
python scripts\run_mvp_demo.py
