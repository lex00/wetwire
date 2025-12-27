#!/usr/bin/env bash
#
# Regenerate AWS CloudFormation resource classes.
#
# This script runs the three-stage codegen pipeline:
# 1. Fetch - Download CloudFormation spec and check botocore version
# 2. Parse - Transform spec to intermediate format
# 3. Generate - Generate Python dataclasses
#
# Usage:
#   ./scripts/regenerate.sh           # Normal run (skips fetch if fresh)
#   ./scripts/regenerate.sh --force   # Force re-fetch of all sources
#   ./scripts/regenerate.sh --dry-run # Show what would be generated
#

set -euo pipefail

# Change to package root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PACKAGE_ROOT"

# Parse arguments
FORCE=""
DRY_RUN=""
VALIDATE=""

for arg in "$@"; do
    case $arg in
        --force)
            FORCE="--force"
            ;;
        --dry-run)
            DRY_RUN="--dry-run"
            ;;
        --validate)
            VALIDATE="--validate"
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Usage: $0 [--force] [--dry-run] [--validate]"
            exit 1
            ;;
    esac
done

echo "wetwire-aws codegen pipeline"
echo "============================"
echo ""

# Stage 1: Fetch
echo "Stage 1/4: Fetching CloudFormation spec..."
python -m codegen.fetch $FORCE
echo ""

# Stage 2: Parse
echo "Stage 2/4: Parsing spec..."
python -m codegen.parse $VALIDATE
echo ""

# Stage 3: Extract enums
echo "Stage 3/4: Extracting enums from botocore..."
python -m codegen.extract_enums
echo ""

# Stage 4: Generate
if [ -n "$DRY_RUN" ]; then
    echo "Stage 4/4: Generating Python classes (dry run)..."
    python -m codegen.generate --dry-run
else
    echo "Stage 4/4: Generating Python classes..."
    python -m codegen.generate
fi
echo ""

echo "============================"
echo "Codegen pipeline complete!"
