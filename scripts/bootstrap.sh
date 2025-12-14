#!/usr/bin/env bash
# Bootstrap script for floe-runtime development environment
set -euo pipefail

echo "=== floe-runtime Bootstrap ==="

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "Please restart your shell or run: source ~/.bashrc"
    exit 0
fi

echo "✓ uv found: $(uv --version)"

# Sync workspace
echo "Syncing workspace..."
uv sync

# Verify installation
echo "Verifying installation..."
uv run python -c "from floe_core import __version__; print(f'floe-core: {__version__}')"

echo ""
echo "=== Bootstrap Complete ==="
echo "Run 'uv run pytest' to run tests"
echo "Run 'uv run mypy --strict packages/' for type checking"
