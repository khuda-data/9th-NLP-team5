@echo off
cd /d "%~dp0"

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

if not exist ".env" (
    copy .env.example .env >nul
    echo.
    echo [!] .env created. Open it and set ANTHROPIC_API_KEY, then run this again.
    echo.
    pause
    exit /b
)

echo.
echo Server starting at http://localhost:8000/docs
echo Press Ctrl+C to stop.
echo.
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
