@echo off
cd /d "%~dp0"

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
if not exist "data" mkdir data

echo ================================================
echo   Paper DB running at http://127.0.0.1:16666
echo   Press Ctrl+C to stop gracefully.
echo ================================================

python -m uvicorn backend.main:app --host 127.0.0.1 --port 16666
