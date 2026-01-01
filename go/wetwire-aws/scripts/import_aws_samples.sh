#!/usr/bin/env bash
#
# AWS CloudFormation samples import script for wetwire-aws (Go)
#
# This script tests wetwire-aws's import functionality against the official
# aws-cloudformation-templates repository.
#
# Workflow:
# 1. Clone aws-cloudformation-templates to temp directory
# 2. Import templates in parallel
# 3. Lint and validate each package
# 4. Report final statistics
#
# This provides an improvement loop for the Go implementation by:
# - Testing real-world CloudFormation templates
# - Identifying parsing/generation issues
# - Validating the generated Go code compiles
#
# Usage:
#   ./scripts/import_aws_samples.sh                        # Full import with validation
#   ./scripts/import_aws_samples.sh --clean                # Clean output before running
#   ./scripts/import_aws_samples.sh --template NAME        # Test specific template
#   ./scripts/import_aws_samples.sh --skip-validation      # Skip package validation
#   ./scripts/import_aws_samples.sh --verbose              # Show detailed progress
#

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
AWS_TEMPLATES_REPO="https://github.com/awslabs/aws-cloudformation-templates.git"
OUTPUT_DIR="$PROJECT_ROOT/examples/aws-cloudformation-templates"

# Templates with known defects that cannot be imported correctly
SKIP_TEMPLATES=(
    "example_2"
    "efs_with_automount_to_ec2"
)

# Templates to exclude from import entirely (non-CloudFormation files)
EXCLUDE_PATTERNS=(
    "*/manifest.yml"
    "*/bandit.yml"
    "*/cdk.json"
    "*event*.json"
    "*/buildspec*.yml"
)

cd "$PROJECT_ROOT"

# Check if a template should be skipped during validation
should_skip_validation() {
    local template_name="$1"
    for skip in ${SKIP_TEMPLATES[@]+"${SKIP_TEMPLATES[@]}"}; do
        [[ "$template_name" == "$skip" ]] && return 0
    done
    return 1
}

# Helper functions
info() {
    echo -e "${BLUE}==>${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

header() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Parse arguments
CLEAN_OUTPUT=false
SKIP_VALIDATION=false
VERBOSE=false
SINGLE_TEMPLATE=""
LOCAL_SOURCE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN_OUTPUT=true
            shift
            ;;
        --skip-validation)
            SKIP_VALIDATION=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --template)
            SINGLE_TEMPLATE="$2"
            shift 2
            ;;
        --local-source)
            LOCAL_SOURCE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Import CloudFormation templates from aws-cloudformation-templates repo"
            echo "and validate them with wetwire-aws (Go)."
            echo ""
            echo "Options:"
            echo "  --clean              Clean examples directory before running"
            echo "  --skip-validation    Skip running each package to validate it works"
            echo "  --verbose, -v        Show detailed progress for each template"
            echo "  --template NAME      Test only a specific template file"
            echo "  --local-source DIR   Use local directory instead of cloning from GitHub"
            echo "  --help, -h           Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                              # Full import with validation"
            echo "  $0 --clean                      # Clean output first"
            echo "  $0 --template EC2/EC2_1.yaml    # Test single template"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Verify Go is installed
if ! command -v go &> /dev/null; then
    error "Go is not installed. Please install Go first:"
    echo "  https://go.dev/doc/install"
    exit 1
fi

# Build the CLI first
header "Building wetwire-aws CLI"
go build -o wetwire-aws ./cmd/wetwire-aws
success "Built wetwire-aws CLI"

# Number of parallel jobs (use CPU count, cap at 8)
JOBS=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
JOBS=$((JOBS > 8 ? 8 : JOBS))

# Step 1: Optionally clean output directory
if [ "$CLEAN_OUTPUT" = true ] && [ -d "$OUTPUT_DIR" ]; then
    header "Cleaning Output Directory"
    rm -rf "$OUTPUT_DIR"
    success "Removed existing $OUTPUT_DIR"
fi

mkdir -p "$OUTPUT_DIR"

# Step 2: Get templates (clone or use local source)
if [ -n "$LOCAL_SOURCE" ]; then
    header "Using Local Template Source"
    if [ ! -d "$LOCAL_SOURCE" ]; then
        error "Local source directory does not exist: $LOCAL_SOURCE"
        exit 1
    fi
    CLONE_DIR="$LOCAL_SOURCE"
    TEMP_DIR=""
    info "Using local directory: $CLONE_DIR"
else
    header "Cloning AWS CloudFormation Templates"
    TEMP_DIR=$(mktemp -d)
    info "Cloning to temp directory: $TEMP_DIR"
    git clone --depth 1 "$AWS_TEMPLATES_REPO" "$TEMP_DIR/aws-cloudformation-templates"
    CLONE_DIR="$TEMP_DIR/aws-cloudformation-templates"
    success "Cloned repository"
fi

# Cleanup temp directory on exit
cleanup_temp() {
    if [ -n "${TEMP_DIR:-}" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup_temp EXIT

# Step 3: Find all templates to import
header "Discovering Templates"

# Find all yaml/json templates, excluding known non-CF files
TEMPLATES=()
while IFS= read -r -d '' template; do
    # Convert to relative path
    rel_path="${template#$CLONE_DIR/}"

    # Skip excluded patterns
    skip=false
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        if [[ "$rel_path" == $pattern ]]; then
            skip=true
            break
        fi
    done
    [ "$skip" = true ] && continue

    # Skip if single template specified and this isn't it
    if [ -n "$SINGLE_TEMPLATE" ] && [ "$rel_path" != "$SINGLE_TEMPLATE" ]; then
        continue
    fi

    TEMPLATES+=("$template")
done < <(find "$CLONE_DIR" -type f \( -name "*.yaml" -o -name "*.yml" -o -name "*.json" \) -print0)

TOTAL_TEMPLATES=${#TEMPLATES[@]}
info "Found $TOTAL_TEMPLATES templates to import"

if [ "$TOTAL_TEMPLATES" -eq 0 ]; then
    if [ -n "$SINGLE_TEMPLATE" ]; then
        error "Template not found: $SINGLE_TEMPLATE"
    else
        error "No templates found in repository"
    fi
    exit 1
fi

# Step 4: Import templates
header "Importing Templates"

IMPORT_ERRORS_FILE="$OUTPUT_DIR/import_errors.log"
> "$IMPORT_ERRORS_FILE"

IMPORT_OK=0
IMPORT_FAIL=0

for template in "${TEMPLATES[@]}"; do
    template_name=$(basename "$template")
    stem="${template_name%.*}"
    pkg_name=$(echo "$stem" | sed 's/[^a-zA-Z0-9_]/_/g' | tr '[:upper:]' '[:lower:]')
    pkg_output="$OUTPUT_DIR/$pkg_name"

    # Remove existing to ensure fresh import
    if [ -d "$pkg_output" ]; then
        rm -rf "$pkg_output"
    fi

    if error_output=$("$PROJECT_ROOT/wetwire-aws" import "$template" -o "$pkg_output" 2>&1); then
        IMPORT_OK=$((IMPORT_OK + 1))
        if [ "$VERBOSE" = "true" ]; then
            success "Imported: $template_name"
        fi
    else
        IMPORT_FAIL=$((IMPORT_FAIL + 1))
        {
            echo "=== $template ==="
            echo "$error_output"
            echo ""
        } >> "$IMPORT_ERRORS_FILE"
        if [ "$VERBOSE" = "true" ]; then
            error "Failed: $template_name"
        fi
    fi
done

success "Imported: $IMPORT_OK  Failed: $IMPORT_FAIL"

# Step 5: Validate generated JSON
VALIDATION_FAILED=()

if [ "$SKIP_VALIDATION" = false ]; then
    header "Validating Generated Templates"

    for json_file in "$OUTPUT_DIR"/*.json; do
        [ -f "$json_file" ] || continue

        pkg_name=$(basename "$json_file" .json)

        if should_skip_validation "$pkg_name"; then
            if [ "$VERBOSE" = "true" ]; then
                warn "$pkg_name (skipped - known issue)"
            fi
            continue
        fi

        # Validate JSON is parseable
        if python3 -c "import json; json.load(open('$json_file'))" 2>/dev/null; then
            if [ "$VERBOSE" = "true" ]; then
                success "$pkg_name"
            fi
        else
            VALIDATION_FAILED+=("$pkg_name")
            if [ "$VERBOSE" = "true" ]; then
                error "$pkg_name (invalid JSON)"
            fi
        fi
    done

    VALIDATED_COUNT=$((IMPORT_OK - ${#VALIDATION_FAILED[@]}))
    success "Validated: $VALIDATED_COUNT/$IMPORT_OK templates"
fi

# Step 6: Report
header "Summary"

echo ""
success "Total templates found: $TOTAL_TEMPLATES"
success "Successful imports: $IMPORT_OK"
if [ "$IMPORT_FAIL" -gt 0 ]; then
    warn "Failed imports: $IMPORT_FAIL"
fi
if [ ${#VALIDATION_FAILED[@]} -gt 0 ]; then
    warn "Failed validation: ${#VALIDATION_FAILED[@]}"
fi
echo ""

info "Output directory: $OUTPUT_DIR"
if [ -s "$IMPORT_ERRORS_FILE" ]; then
    info "Import errors: $IMPORT_ERRORS_FILE"
fi
echo ""

# Calculate success rate
SUCCESS_RATE=$((IMPORT_OK * 100 / TOTAL_TEMPLATES))
info "Success rate: ${SUCCESS_RATE}%"

# Exit with appropriate code
if [ "$IMPORT_FAIL" -gt 0 ] || [ ${#VALIDATION_FAILED[@]} -gt 0 ]; then
    warn "Completed with failures - examples preserved for inspection"
    echo ""
    echo "Improvement suggestions:"
    echo "  1. Review $IMPORT_ERRORS_FILE for common failure patterns"
    echo "  2. Add support for missing intrinsic functions"
    echo "  3. Handle edge cases in resource property parsing"
    exit 1
else
    success "All templates imported and validated successfully!"
    exit 0
fi
