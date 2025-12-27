#!/usr/bin/env bash
#
# Set up development environment with generated resources.
#
# This script is for first-time setup after cloning. It generates the
# AWS CloudFormation resource classes needed for development and testing.
#
# Usage:
#   ./scripts/dev-setup.sh           # Generate resources (skips if exist)
#   ./scripts/dev-setup.sh --force   # Force regeneration
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PACKAGE_ROOT"

FORCE=""
for arg in "$@"; do
    case $arg in
        --force)
            FORCE="--force"
            ;;
        -h|--help)
            echo "Usage: $0 [--force]"
            echo ""
            echo "Options:"
            echo "  --force    Force regeneration even if resources exist"
            echo ""
            exit 0
            ;;
    esac
done

echo "wetwire-aws Development Setup"
echo "=============================="
echo ""

# Check if resources already exist
RESOURCES_DIR="$PACKAGE_ROOT/src/wetwire_aws/resources"
INIT_FILE="$RESOURCES_DIR/__init__.py"

if [ -f "$INIT_FILE" ] && [ -z "$FORCE" ]; then
    # Count service directories to verify completeness
    SERVICE_COUNT=$(find "$RESOURCES_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
    if [ "$SERVICE_COUNT" -ge 10 ]; then
        echo "Resources already exist ($SERVICE_COUNT services found)."
        echo "Use --force to regenerate."
        echo ""
        echo "Tip: Run './scripts/regenerate.sh' for explicit regeneration."
        exit 0
    fi
fi

# Check for codegen dependencies
echo "Checking codegen dependencies..."
MISSING_DEPS=""
python -c "import requests" 2>/dev/null || MISSING_DEPS="$MISSING_DEPS requests"
python -c "import jinja2" 2>/dev/null || MISSING_DEPS="$MISSING_DEPS jinja2"
python -c "import botocore" 2>/dev/null || MISSING_DEPS="$MISSING_DEPS botocore"
python -c "import black" 2>/dev/null || MISSING_DEPS="$MISSING_DEPS black"

if [ -n "$MISSING_DEPS" ]; then
    echo "Installing missing codegen dependencies:$MISSING_DEPS"
    if command -v uv &> /dev/null; then
        uv pip install $MISSING_DEPS
    else
        pip install $MISSING_DEPS
    fi
fi
echo ""

# Run the codegen pipeline
echo "Generating AWS CloudFormation resources..."
echo ""
./scripts/regenerate.sh $FORCE

echo ""
echo "Development setup complete!"
echo ""
echo "Next steps:"
echo "  1. Install the package: uv pip install -e ."
echo "  2. Run tests: uv run pytest"
echo ""
