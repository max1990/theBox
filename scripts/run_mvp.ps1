if (!(Test-Path .venv)) { py -3.11 -m venv .venv }
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
if (Test-Path .\pyproject.toml) { pip install -e . } else { pip install pydantic pytest }
pytest -q
python .\scripts\run_mvp_demo.py
