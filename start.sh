#!/bin/bash
set -e

command -v python3 >/dev/null 2>&1 || { echo "Python 3 is not installed."; exit 1; }
command -v pip3 >/dev/null 2>&1 || { echo "pip3 is not installed."; exit 1; }

if [ ! -d "venv-posix" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv-posix
fi

echo "Installing requirements..."
venv-posix/bin/python3 -m pip install -r requirements.txt

echo "Starting The Box..."
venv-posix/bin/python3 app.py "$@"
