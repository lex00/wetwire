#!/usr/bin/env bash
#
# Run the same checks as CI locally.
#
# Usage:
#   ./scripts/ci.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PACKAGE_ROOT"

echo "=== wetwire-agent Go CI checks ==="
echo ""

# Verify Go is installed
if ! command -v go &> /dev/null; then
    echo "Error: go is not installed"
    exit 1
fi

# Download dependencies
echo ">>> Downloading dependencies..."
go mod download
echo ""

# Lint (if golangci-lint is available)
if command -v golangci-lint &> /dev/null; then
    echo ">>> Running golangci-lint..."
    golangci-lint run ./...
    echo ""
else
    echo ">>> Skipping lint (golangci-lint not installed)"
    echo "    Install with: go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest"
    echo ""
fi

# Tests
echo ">>> Running tests..."
go test -v -race ./...
echo ""

# Build
echo ">>> Building CLI..."
go build -v ./cmd/wetwire-agent
echo ""

# Verify CLI works
echo ">>> Verifying CLI..."
./wetwire-agent list personas
echo ""

echo "=== All checks passed! ==="
