#!/usr/bin/env bash
#
# AWS CloudFormation samples import script for wetwire-aws
#
# This script tests wetwire-aws's import functionality against the official
# aws-cloudformation-templates repository.
#
# Workflow:
# 1. Clone aws-cloudformation-templates to temp directory
# 2. Apply template fixes
# 3. Import templates in parallel
# 4. Lint packages to fix forward references
# 5. Validate each package in parallel
# 6. Report final statistics
#
# On failure, the examples directory is preserved for inspection.
# On success with --clean flag, examples are removed.
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
# These will be skipped during validation (but still imported for inspection)
SKIP_TEMPLATES=(
    # Uses custom CloudFormation macro (ExecutionRoleBuilder) with non-standard properties
    "example_2"
    # Has complex Join-based UserData that generates malformed Python strings
    "efs_with_automount_to_ec2"
)

# Templates to exclude from import entirely (Rain-specific, Kubernetes manifests, etc.)
# These use non-standard CloudFormation features that require preprocessing
EXCLUDE_TEMPLATES=(
    # Rain-specific templates (use !Rain:: tags)
    "APIGateway/apigateway_lambda_integration.yaml"
    "CloudFormation/CustomResources/getfromjson/src/getfromjson.yml"
    "CloudFormation/MacrosExamples/Boto3/example.json"
    "CloudFormation/MacrosExamples/DateFunctions/date_example.yaml"
    "CloudFormation/MacrosExamples/DateFunctions/date.yaml"
    "CloudFormation/MacrosExamples/PyPlate/python.yaml"
    "CloudFormation/MacrosExamples/StringFunctions/string.yaml"
    "CloudFormation/StackSets/common-resources-stackset_1.yaml"
    "CloudFormation/StackSets/common-resources.yaml"
    "CloudFormation/StackSets/common-resources.json"
    "CloudFormation/StackSets/log-setup-management_1.yaml"
    "ElastiCache/Elasticache-snapshot.yaml"
    "IoT/amzn2-greengrass-cfn.yaml"
    "RainModules/api-resource.yml"
    "RainModules/bucket-policy.yml"
    "RainModules/bucket.yml"
    "RainModules/static-site.yml"
    "Solutions/GitLab/GitLabServer.yaml"
    "Solutions/GitLab/GitLabServer.json"
    "Solutions/GitLabAndVSCode/GitLabAndVSCode.yaml"
    "Solutions/GitLabAndVSCode/GitLabAndVSCode.json"
    "Solutions/Gitea/Gitea.yaml"
    "Solutions/Gitea/Gitea.json"
    "Solutions/Gitea/Gitea-pkg.yaml"
    "Solutions/Gitea/Gitea-pkg.json"
    "Solutions/ManagedAD/templates/MANAGEDAD.cfn.yaml"
    "Solutions/ManagedAD/templates/MANAGEDAD.cfn.json"
    "Solutions/VSCode/VSCodeServer.yaml"
    "Solutions/VSCode/VSCodeServer.json"
    # Kubernetes manifests (not CloudFormation)
    "EKS/manifest.yml"
    # Lambda test events (not CloudFormation templates)
    "CloudFormation/CustomResources/getfromjson/src/events/event-consume-from-list.json"
    "CloudFormation/CustomResources/getfromjson/src/events/event-consume-from-list-retrieval-error.json"
    "CloudFormation/CustomResources/getfromjson/src/events/event-consume-from-map.json"
    "CloudFormation/CustomResources/getfromjson/src/events/event-consume-from-map-retrieval-error.json"
    "CloudFormation/CustomResources/getfromjson/src/events/event-empty-json-data-input.json"
    "CloudFormation/CustomResources/getfromjson/src/events/event-empty-search-input.json"
    "CloudFormation/CustomResources/getfromjson/src/events/event-invalid-json-data-input.json"
    "CloudFormation/CustomResources/getfromjson/src/events/event-invalid-search-input.json"
    # SAM templates (use Transform: AWS::Serverless)
    "CloudFormation/CustomResources/getfromjson/src/template.yml"
    "CloudFormation/MacrosExamples/Count/template.json"
    "CloudFormation/MacrosExamples/Count/template.yaml"
    # EKS templates (too complex, many forward reference issues)
    "EKS/template.json"
    "EKS/template.yaml"
    # Macro definition templates (just define the macro, no resources to validate)
    "CloudFormation/MacrosExamples/Count/macro.json"
    "CloudFormation/MacrosExamples/Count/macro.yaml"
    "CloudFormation/MacrosExamples/StackMetrics/macro.json"
    "CloudFormation/MacrosExamples/StackMetrics/macro.yaml"
    "CloudFormation/MacrosExamples/S3Objects/macro.json"
    "CloudFormation/MacrosExamples/S3Objects/macro.yaml"
    "CloudFormation/MacrosExamples/Explode/macro.json"
    "CloudFormation/MacrosExamples/Explode/macro.yaml"
    "CloudFormation/MacrosExamples/ExecutionRoleBuilder/macro.json"
    "CloudFormation/MacrosExamples/ExecutionRoleBuilder/macro.yaml"
    "CloudFormation/MacrosExamples/Boto3/macro.json"
    "CloudFormation/MacrosExamples/Boto3/macro.yaml"
    # CodeBuild buildspec files (not CloudFormation templates)
    "Solutions/CodeBuildAndCodePipeline/codebuild-app-build.yml"
    "Solutions/CodeBuildAndCodePipeline/codebuild-app-deploy.yml"
    # Custom resource consumer example templates (reference custom resources that don't exist)
    "CloudFormation/CustomResources/getfromjson/example-templates/getfromjson-consumer.yml"
    # Bandit security linter config (not CloudFormation)
    "CloudFormation/CustomResources/getfromjson/bandit.yml"
    "CloudFormation/CustomResources/getfromjson/bandit.json"
    # CDK configuration files (not CloudFormation)
    "CloudFormation/StackSets-CDK/cdk.json"
    "CloudFormation/StackSets-CDK/config.json"
    # Macro test events (not CloudFormation templates)
    "CloudFormation/MacrosExamples/Count/event.json"
    "CloudFormation/MacrosExamples/Count/event_bad.json"
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
            echo "and validate them with wetwire-aws."
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
            echo "  $0 --local-source /path/to/templates  # Use local templates"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Verify uv is installed
if ! command -v uv &> /dev/null; then
    error "uv is not installed. Please install uv first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

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

# Cleanup temp directory on exit (but NOT the examples directory or local source)
cleanup_temp() {
    if [ -n "${TEMP_DIR:-}" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
    if [ -n "${RESULTS_FILE:-}" ] && [ -f "$RESULTS_FILE" ]; then
        rm -f "$RESULTS_FILE"
    fi
    if [ -n "${IMPORT_RESULTS_FILE:-}" ] && [ -f "$IMPORT_RESULTS_FILE" ]; then
        rm -f "$IMPORT_RESULTS_FILE"
    fi
}
trap cleanup_temp EXIT

# Step 3: Apply template fixes
header "Applying Template Fixes"
uv run python "$SCRIPT_DIR/fix_templates.py" "$CLONE_DIR"

# Step 4: Remove excluded templates
header "Removing Excluded Templates"
EXCLUDED_COUNT=0
for template in "${EXCLUDE_TEMPLATES[@]}"; do
    template_path="$CLONE_DIR/$template"
    if [ -f "$template_path" ]; then
        rm -f "$template_path"
        EXCLUDED_COUNT=$((EXCLUDED_COUNT + 1))
    fi
done
info "Removed $EXCLUDED_COUNT excluded templates (Rain-specific, Kubernetes, etc.)"

# Step 5: Find all templates to import
header "Discovering Templates"

# Find all yaml/json templates
TEMPLATES=()
while IFS= read -r -d '' template; do
    # Convert to relative path
    rel_path="${template#$CLONE_DIR/}"

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

# Step 6: Import templates in parallel
header "Importing Templates (${JOBS} parallel jobs)"

IMPORT_ERRORS_FILE="$OUTPUT_DIR/import_errors.log"
> "$IMPORT_ERRORS_FILE"

export OUTPUT_DIR PROJECT_ROOT IMPORT_ERRORS_FILE VERBOSE

import_template() {
    local template="$1"
    local template_name=$(basename "$template")
    local stem="${template_name%.*}"
    local pkg_name=$(echo "$stem" | sed 's/[^a-zA-Z0-9_]/_/g' | tr '[:upper:]' '[:lower:]')
    local pkg_output="$OUTPUT_DIR/$pkg_name"

    # Skip if already exists
    if [ -d "$pkg_output" ]; then
        echo "SKIP:$pkg_name"
        return
    fi

    local error_output
    if error_output=$(cd "$PROJECT_ROOT" && uv run wetwire-aws import "$template" -o "$pkg_output" 2>&1); then
        echo "OK:$pkg_name"
        if [ "$VERBOSE" = "true" ]; then
            echo "  Imported: $template_name -> $pkg_name" >&2
        fi
    else
        echo "FAIL:$pkg_name"
        {
            echo "=== $template ==="
            echo "$error_output"
            echo ""
        } >> "$IMPORT_ERRORS_FILE"
    fi
}
export -f import_template

# Create temp file for import results
IMPORT_RESULTS_FILE=$(mktemp)

# Run imports in parallel
printf '%s\n' "${TEMPLATES[@]}" | xargs -P "$JOBS" -I {} bash -c 'import_template "$@"' _ {} > "$IMPORT_RESULTS_FILE"

# Count import results
IMPORT_OK=0
IMPORT_FAIL=0
IMPORT_SKIP=0
while IFS=: read -r status pkg_name; do
    case "$status" in
        OK) IMPORT_OK=$((IMPORT_OK + 1)) ;;
        FAIL) IMPORT_FAIL=$((IMPORT_FAIL + 1)) ;;
        SKIP) IMPORT_SKIP=$((IMPORT_SKIP + 1)) ;;
    esac
done < "$IMPORT_RESULTS_FILE"

success "Imported: $IMPORT_OK  Failed: $IMPORT_FAIL  Skipped: $IMPORT_SKIP"

# Step 7: Lint packages to fix forward references and other issues
header "Linting Packages"

LINT_ERRORS_FILE="$OUTPUT_DIR/lint_errors.log"
> "$LINT_ERRORS_FILE"

if ! uv run wetwire-aws lint --fix "$OUTPUT_DIR" 2> "$LINT_ERRORS_FILE"; then
    warn "Some lint issues could not be fixed (see $LINT_ERRORS_FILE)"
else
    success "Linted all packages"
fi

# Step 8: Validate packages
VALIDATION_FAILED=()

if [ "$SKIP_VALIDATION" = false ]; then
    header "Validating Packages (${JOBS} parallel jobs)"

    # Get list of package directories
    PACKAGE_DIRS=()
    for dir in "$OUTPUT_DIR"/*/; do
        if [ -d "$dir" ]; then
            PACKAGE_DIRS+=("$dir")
        fi
    done

    TOTAL_PACKAGES=${#PACKAGE_DIRS[@]}

    if [ "$TOTAL_PACKAGES" -eq 0 ]; then
        warn "No packages to validate"
    else
        # Create a temporary file to track results
        RESULTS_FILE=$(mktemp)

        export PROJECT_SRC="$PROJECT_ROOT/src"
        export VALIDATION_ERRORS_FILE="$OUTPUT_DIR/validation_errors.log"
        > "$VALIDATION_ERRORS_FILE"

        validate_package() {
            local pkg_dir="$1"
            local outer_name=$(basename "$pkg_dir")

            # Find the actual package name (inner directory) - may differ in case
            local inner_pkg=""
            for d in "$pkg_dir"/*/; do
                if [ -f "$d/__init__.py" ]; then
                    inner_pkg=$(basename "$d")
                    break
                fi
            done

            if [ -z "$inner_pkg" ]; then
                echo "FAIL:$outer_name"
                {
                    echo "=== $outer_name ==="
                    echo "No __init__.py found in package"
                    echo ""
                } >> "$VALIDATION_ERRORS_FILE"
                return
            fi

            # Validate by importing the package - this tests that:
            # 1. All modules can be loaded
            # 2. All class definitions execute without error
            # 3. All ref()/get_att() references resolve
            local error_output
            if error_output=$(cd "$PROJECT_ROOT" && PYTHONPATH="$PROJECT_SRC:$pkg_dir" uv run python -c "import $inner_pkg" 2>&1); then
                echo "OK:$outer_name"
            else
                echo "FAIL:$outer_name"
                {
                    echo "=== $outer_name ($inner_pkg) ==="
                    echo "$error_output"
                    echo ""
                } >> "$VALIDATION_ERRORS_FILE"
            fi
        }
        export -f validate_package

        # Run validations in parallel, filtering out skipped packages
        for pkg_dir in "${PACKAGE_DIRS[@]}"; do
            pkg_name=$(basename "$pkg_dir")
            if should_skip_validation "$pkg_name"; then
                warn "$pkg_name (skipped - known malformed template)"
            else
                echo "$pkg_dir"
            fi
        done | xargs -P "$JOBS" -I {} bash -c 'validate_package "$@"' _ {} >> "$RESULTS_FILE"

        # Process results
        VALIDATED_COUNT=0
        while IFS=: read -r status pkg_name; do
            if [ "$status" = "OK" ]; then
                if [ "$VERBOSE" = "true" ]; then
                    success "$pkg_name"
                fi
                VALIDATED_COUNT=$((VALIDATED_COUNT + 1))
            else
                error "$pkg_name"
                VALIDATION_FAILED+=("$pkg_name")
            fi
        done < "$RESULTS_FILE"

        success "Validated: $VALIDATED_COUNT/$TOTAL_PACKAGES packages"
    fi
else
    warn "Skipping validation (--skip-validation flag)"
fi

# Step 9: Report
header "Summary"

FINAL_DIRS=$(find "$OUTPUT_DIR" -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
FINAL_DIRS=$((FINAL_DIRS - 1))  # Exclude output dir itself

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
if [ -s "$OUTPUT_DIR/validation_errors.log" ]; then
    info "Validation errors: $OUTPUT_DIR/validation_errors.log"
fi
echo ""

# Exit with appropriate code
if [ "$IMPORT_FAIL" -gt 0 ] || [ ${#VALIDATION_FAILED[@]} -gt 0 ]; then
    warn "Completed with failures - examples preserved for inspection"
    exit 1
else
    success "All templates imported and validated successfully!"
    exit 0
fi
