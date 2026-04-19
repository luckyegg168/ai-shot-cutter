@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo   AI Shot Cutter — Install Script (Windows)
echo   Powered by uv package manager
echo ============================================================
echo.

:: ── 1. Check uv ──────────────────────────────────────────────
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO]  uv not found. Installing uv...
    powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install uv. Please install it manually:
        echo         https://docs.astral.sh/uv/getting-started/installation/
        exit /b 1
    )
    :: Reload PATH so uv is available in this session
    set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
    echo [OK]    uv installed successfully.
) else (
    for /f "tokens=*" %%v in ('uv --version 2^>^&1') do echo [OK]    Found %%v
)
echo.

:: ── 2. Check Python ≥ 3.11 ───────────────────────────────────
echo [INFO]  Checking Python version...
uv python find 3.11 >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO]  Python 3.11+ not found via uv. Fetching Python 3.11...
    uv python install 3.11
    if %errorlevel% neq 0 (
        echo [ERROR] Could not install Python 3.11. Please install it manually:
        echo         https://www.python.org/downloads/
        exit /b 1
    )
)
echo [OK]    Python 3.11+ available.
echo.

:: ── 3. Create / sync virtual environment ─────────────────────
echo [INFO]  Creating virtual environment in .venv ...
uv venv --python 3.11
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    exit /b 1
)
echo [OK]    Virtual environment ready at .venv\
echo.

:: ── 4. Install runtime + dev dependencies ────────────────────
echo [INFO]  Installing dependencies from pyproject.toml ...
uv sync --all-groups
if %errorlevel% neq 0 (
    echo [ERROR] Dependency installation failed. Check the error above.
    exit /b 1
)
echo [OK]    All packages installed.
echo.

:: ── 5. Check ffmpeg ──────────────────────────────────────────
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN]  ffmpeg not found on PATH.
    echo         The app requires ffmpeg to extract video frames.
    echo         Download from: https://ffmpeg.org/download.html
    echo         Then add the bin\ folder to your PATH environment variable.
) else (
    for /f "tokens=*" %%v in ('ffmpeg -version 2^>^&1 ^| findstr /i "ffmpeg version"') do (
        echo [OK]    %%v
        goto ffmpeg_done
    )
    :ffmpeg_done
)
echo.

:: ── 6. Summary ───────────────────────────────────────────────
echo ============================================================
echo   Setup complete!
echo.
echo   Activate the environment:
echo     .venv\Scripts\activate
echo.
echo   Run the app:
echo     uv run python main.py
echo.
echo   Run tests:
echo     uv run pytest tests\
echo ============================================================
endlocal
