@echo off
:: AI Shot Cutter — Run launcher (Windows)
:: Uses uv to run inside the project's virtual environment.

cd /d "%~dp0"

where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] uv is not installed. Please run install.bat first.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo [ERROR] Virtual environment not found. Please run install.bat first.
    pause
    exit /b 1
)

uv run python main.py %*
