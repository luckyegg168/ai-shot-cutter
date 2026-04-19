#!/usr/bin/env bash
# ============================================================
#   AI Shot Cutter — Install Script (macOS / Linux)
#   Powered by uv package manager
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

ok()   { echo -e "${GREEN}[OK]   ${NC} $*"; }
info() { echo -e "       [INFO]  $*"; }
warn() { echo -e "${YELLOW}[WARN] ${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

echo "============================================================"
echo "  AI Shot Cutter — Install Script (macOS / Linux)"
echo "  Powered by uv package manager"
echo "============================================================"
echo

# ── 1. Check / install uv ────────────────────────────────────
if ! command -v uv &>/dev/null; then
    info "uv not found. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH for this session
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    command -v uv &>/dev/null || err "uv installation failed. Install manually: https://docs.astral.sh/uv/getting-started/installation/"
    ok "uv installed successfully."
else
    ok "Found $(uv --version)"
fi
echo

# ── 2. Check Python ≥ 3.11 ───────────────────────────────────
info "Checking Python 3.11+ ..."
if ! uv python find 3.11 &>/dev/null; then
    info "Python 3.11+ not found via uv. Fetching Python 3.11..."
    uv python install 3.11 || err "Could not install Python 3.11. Install manually: https://www.python.org/downloads/"
fi
ok "Python 3.11+ available."
echo

# ── 3. Create / sync virtual environment ─────────────────────
info "Creating virtual environment in .venv ..."
uv venv --python 3.11
ok "Virtual environment ready at .venv/"
echo

# ── 4. Install runtime + dev dependencies ────────────────────
info "Installing dependencies from pyproject.toml ..."
uv sync --all-groups
ok "All packages installed."
echo

# ── 5. Check ffmpeg ──────────────────────────────────────────
if ! command -v ffmpeg &>/dev/null; then
    warn "ffmpeg not found on PATH."
    warn "The app requires ffmpeg to extract video frames."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        warn "Install via Homebrew:  brew install ffmpeg"
    else
        warn "Install via apt:       sudo apt install ffmpeg"
        warn "Install via dnf:       sudo dnf install ffmpeg"
    fi
else
    FFVER=$(ffmpeg -version 2>&1 | head -1)
    ok "$FFVER"
fi
echo

# ── 6. Summary ───────────────────────────────────────────────
echo "============================================================"
echo "  Setup complete!"
echo
echo "  Activate the environment:"
echo "    source .venv/bin/activate"
echo
echo "  Run the app:"
echo "    uv run python main.py"
echo
echo "  Run tests:"
echo "    uv run pytest tests/"
echo "============================================================"
