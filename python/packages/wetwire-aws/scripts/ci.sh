#!/usr/bin/env bash
#
# Run the same checks as CI locally.
#
# Usage:
#   ./scripts/ci.sh          # Run all checks
#   ./scripts/ci.sh --quick  # Skip resource generation (if already done)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PACKAGE_ROOT"

QUICK=""
for arg in "$@"; do
    case $arg in
        --quick)
            QUICK="1"
            ;;
    esac
done

echo "=== wetwire-aws CI checks ==="
echo ""

# Generate resources if needed
if [ -z "$QUICK" ] || [ ! -d "src/wetwire_aws/resources" ]; then
    echo ">>> Generating resources..."
    ./scripts/regenerate.sh
    echo ""
fi

# Lint
echo ">>> Running ruff check..."
uv run ruff check src/wetwire_aws --exclude resources
echo ""

echo ">>> Checking formatting..."
uv run ruff format --check src/wetwire_aws --exclude resources
echo ""

# Tests
echo ">>> Running tests..."
uv run pytest -q
echo ""

echo "=== All checks passed! ==="
