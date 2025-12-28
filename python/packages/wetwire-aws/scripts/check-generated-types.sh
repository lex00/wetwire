#!/usr/bin/env bash
#
# Check type hints in generated resource code.
#
# Run this periodically to identify improvements for the code generator.
# Generated resources are excluded from regular CI to avoid noise.
#
# Usage:
#   ./scripts/check-generated-types.sh           # Summary of errors by category
#   ./scripts/check-generated-types.sh --full    # Full mypy output
#   ./scripts/check-generated-types.sh --count   # Just error counts per service
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PACKAGE_ROOT"

MODE="summary"
for arg in "$@"; do
    case $arg in
        --full)
            MODE="full"
            ;;
        --count)
            MODE="count"
            ;;
    esac
done

echo "=== Checking generated resource types ==="
echo ""

# Ensure resources exist
if [ ! -d "src/wetwire_aws/resources" ]; then
    echo "Resources not found. Run ./scripts/regenerate.sh first."
    exit 1
fi

# Mypy args: ignore pyproject.toml config (which excludes resources)
MYPY_CMD="uv run mypy src/wetwire_aws/resources --config-file /dev/null --show-error-codes"

case $MODE in
    full)
        echo "Full mypy output:"
        echo ""
        $MYPY_CMD 2>&1 || true
        ;;
    count)
        echo "Error counts by service:"
        echo ""
        $MYPY_CMD 2>&1 | \
            grep "^src/wetwire_aws/resources/" | \
            sed 's|src/wetwire_aws/resources/\([^/]*\)/.*|\1|' | \
            sort | uniq -c | sort -rn || true
        ;;
    summary)
        echo "Error summary by type:"
        echo ""
        OUTPUT=$($MYPY_CMD 2>&1 || true)

        # Count by error code
        echo "By error code:"
        echo "$OUTPUT" | grep -oE '\[[-a-z]+\]' | sort | uniq -c | sort -rn || true
        echo ""

        # Count by service (top 10)
        echo "Top 10 services by error count:"
        echo "$OUTPUT" | \
            grep "^src/wetwire_aws/resources/" | \
            sed 's|src/wetwire_aws/resources/\([^/]*\)/.*|\1|' | \
            sort | uniq -c | sort -rn | head -10 || true
        echo ""

        # Total
        TOTAL=$(echo "$OUTPUT" | grep -c "error:" || echo "0")
        echo "Total errors: $TOTAL"
        ;;
esac

echo ""
echo "=== Done ==="
