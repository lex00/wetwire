#!/bin/bash
# Run ruff and black on both wetwire packages
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Linting wetwire core ==="
cd "$PYTHON_DIR/packages/wetwire"
uv run ruff check --fix .
uv run black .

echo ""
echo "=== Linting wetwire-aws ==="
cd "$PYTHON_DIR/packages/wetwire-aws"
uv run ruff check --fix .
uv run black .

echo ""
echo "=== All linting passed ==="
