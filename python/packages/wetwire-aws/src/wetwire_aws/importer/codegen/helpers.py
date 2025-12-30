"""Helper utilities and constants for code generation.

This module provides utility functions and mappings used throughout
the code generation process.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wetwire_aws.linter.splitting import (
    EC2_NETWORK_TYPES,
    SERVICE_CATEGORIES,
    categorize_resource_type,
)
from wetwire_aws.naming import sanitize_class_name, to_pascal_case, to_snake_case

if TYPE_CHECKING:
    from wetwire_aws.importer.ir import IRResource

# Re-export for convenience
__all__ = [
    "sanitize_class_name",
    "to_pascal_case",
    "to_snake_case",
    "get_resource_category",
    "resolve_resource_type",
    "resolve_property_type",
    "get_property_type_info",
    "find_property_type_for_cf_keys",
    "extract_class_from_type_hint",
    "SERVICE_CATEGORIES",
    "EC2_NETWORK_TYPES",
    "PARAMETER_TYPE_MAP",
    "PSEUDO_PARAMETER_MAP",
]


def get_resource_category(resource: IRResource) -> str:
    """Get the category file for a resource based on its AWS service.

    Maps AWS service names to category files (compute.py, network.py, etc.).
    Special handling for EC2 VPC/networking resources.

    Args:
        resource: The IR resource to categorize.

    Returns:
        Category name for the file (e.g., "compute", "network", "main").

    Example:
        >>> # EC2 instances go to compute
        >>> get_resource_category(ec2_instance_resource)
        'compute'
        >>> # EC2 VPCs go to network (special case)
        >>> get_resource_category(vpc_resource)
        'network'
    """
    return categorize_resource_type(resource.resource_type)


# =============================================================================
# Resource Type Resolution
# =============================================================================

# Map CloudFormation service names to wetwire_aws module names
SERVICE_TO_MODULE: dict[str, str] = {
    # Handle special cases where CF service name differs from module name
    "Lambda": "lambda_",  # lambda is a Python keyword
    "ElasticLoadBalancing": "elasticloadbalancing",
    "ElasticLoadBalancingV2": "elasticloadbalancingv2",
    "StepFunctions": "stepfunctions",
    "CloudFormation": "cloudformation",
    "CloudWatch": "cloudwatch",
    "CloudFront": "cloudfront",
    "CloudTrail": "cloudtrail",
    "SecretsManager": "secretsmanager",
    "EventBridge": "events",  # EventBridge uses events module
    "ApiGatewayV2": "apigatewayv2",
    "APIGateway": "apigateway",
    "CodeBuild": "codebuild",
    "CodePipeline": "codepipeline",
    "CodeCommit": "codecommit",
    "CodeDeploy": "codedeploy",
    "ServiceCatalog": "servicecatalog",
    # Most services use lowercase version of CF name
}


def resolve_resource_type(cf_type: str) -> tuple[str, str] | None:
    """Resolve a CloudFormation resource type to (module, class) tuple.

    Args:
        cf_type: CloudFormation resource type (e.g., "AWS::S3::Bucket")

    Returns:
        Tuple of (module_name, class_name) or None if not recognized.

    Example:
        >>> resolve_resource_type("AWS::S3::Bucket")
        ('s3', 'Bucket')
        >>> resolve_resource_type("AWS::Lambda::Function")
        ('lambda_', 'Function')
    """
    if not cf_type.startswith("AWS::"):
        return None

    parts = cf_type.split("::")
    if len(parts) != 3:
        return None

    _, service, type_name = parts

    # Get module name (handle special cases)
    module = SERVICE_TO_MODULE.get(service, service.lower())

    # Check if the module and class actually exist in wetwire_aws.resources
    if not _resource_class_exists(module, type_name):
        return None

    return (module, type_name)


# Cache for known resource classes: {(module, class_name): exists}
_KNOWN_RESOURCE_CLASSES: dict[tuple[str, str], bool] | None = None


def _resource_class_exists(module_name: str, class_name: str) -> bool:
    """Check if a resource class exists in wetwire_aws.resources.

    Args:
        module_name: The module name (e.g., 's3', 'lambda_')
        class_name: The class name (e.g., 'Bucket', 'Function')

    Returns:
        True if the class exists in the module, False otherwise.
    """
    global _KNOWN_RESOURCE_CLASSES

    if _KNOWN_RESOURCE_CLASSES is None:
        # Build cache by scanning module files for class definitions
        import re
        from pathlib import Path

        _KNOWN_RESOURCE_CLASSES = {}
        try:
            import wetwire_aws.resources as resources_pkg

            resources_dir = Path(resources_pkg.__file__).parent

            for entry in resources_dir.iterdir():
                if entry.name.startswith("_"):
                    continue

                mod_name = None
                init_file = None

                if entry.is_dir() and (entry / "__init__.py").exists():
                    mod_name = entry.name
                    init_file = entry / "__init__.py"
                elif entry.is_file() and entry.suffix == ".py":
                    mod_name = entry.stem
                    init_file = entry

                if mod_name and init_file and init_file.exists():
                    try:
                        content = init_file.read_text()
                        # Find all class definitions
                        for match in re.finditer(
                            r"^class\s+(\w+)", content, re.MULTILINE
                        ):
                            _KNOWN_RESOURCE_CLASSES[(mod_name, match.group(1))] = True
                    except Exception:
                        pass

        except (ImportError, AttributeError):
            pass

    return _KNOWN_RESOURCE_CLASSES.get((module_name, class_name), False)


# Import parameter mappings from constants (re-exported for backwards compatibility)
from wetwire_aws.constants import PARAMETER_TYPE_MAP, PSEUDO_PARAMETER_MAP  # noqa: E402

# =============================================================================
# PropertyType Registry
# =============================================================================

# Cache for PropertyType mappings: {(module, class_name): info_dict}
_PROPERTY_TYPE_MAP: dict[tuple[str, str], dict[str, Any]] | None = None

# Reverse lookup: {cf_key: [(module, class_name), ...]}
_CF_PROPERTY_TO_CLASSES: dict[str, list[tuple[str, str]]] | None = None


def _build_property_type_map() -> None:
    """Build mapping of PropertyType classes and their field information.

    Scans resources/*/*.py (e.g., s3/bucket.py) for PropertyType subclasses
    and extracts their field names. Uses convention-based CF name mapping
    (snake_case → PascalCase).
    """
    global _PROPERTY_TYPE_MAP, _CF_PROPERTY_TO_CLASSES

    if _PROPERTY_TYPE_MAP is not None:
        return

    import re
    from pathlib import Path

    _PROPERTY_TYPE_MAP = {}
    _CF_PROPERTY_TO_CLASSES = {}

    try:
        import wetwire_aws.resources as resources_pkg

        resources_dir = Path(resources_pkg.__file__).parent
    except (ImportError, AttributeError):
        return

    # Pattern to match class definitions with parent
    class_pattern = re.compile(r"^class\s+(\w+)\s*\(\s*PropertyType\s*\)")
    # Pattern to match field definitions
    field_pattern = re.compile(r"^\s{4}(\w+):\s*(.+?)\s*(?:=|$)")

    def process_file(py_file: Path, module_name: str) -> None:
        """Scan a Python file for PropertyType classes."""
        try:
            content = py_file.read_text()
        except Exception:
            return

        current_class: str | None = None
        current_fields: dict[str, str] = {}
        in_class = False

        for line in content.split("\n"):
            # Check for PropertyType class definition
            class_match = class_pattern.match(line)
            if class_match:
                # Save previous class
                if current_class and current_fields:
                    _register_property_type(module_name, current_class, current_fields)
                current_class = class_match.group(1)
                current_fields = {}
                in_class = True
                continue

            # Check for non-PropertyType class (ends current PropertyType)
            if line.startswith("class ") and "PropertyType" not in line:
                if current_class and current_fields:
                    _register_property_type(module_name, current_class, current_fields)
                current_class = None
                current_fields = {}
                in_class = False
                continue

            # Parse field definitions within PropertyType
            if in_class and current_class:
                field_match = field_pattern.match(line)
                if field_match:
                    field_name = field_match.group(1)
                    field_type = field_match.group(2)
                    if not field_name.startswith("_"):
                        current_fields[field_name] = field_type

        # Don't forget the last class
        if current_class and current_fields:
            _register_property_type(module_name, current_class, current_fields)

    def _register_property_type(
        module_name: str, class_name: str, fields: dict[str, str]
    ) -> None:
        """Register a PropertyType class in the registry."""
        key = (module_name, class_name)

        # Build CF → Python name mapping using convention
        cf_to_python: dict[str, str] = {}
        for field_name in fields:
            cf_name = to_pascal_case(field_name)
            cf_to_python[cf_name] = field_name

        _PROPERTY_TYPE_MAP[key] = {
            "cf_to_python": cf_to_python,
            "python_to_cf": {v: k for k, v in cf_to_python.items()},
            "field_types": fields.copy(),
        }

        # Build reverse lookup
        for cf_name in cf_to_python:
            if cf_name not in _CF_PROPERTY_TO_CLASSES:
                _CF_PROPERTY_TO_CLASSES[cf_name] = []
            _CF_PROPERTY_TO_CLASSES[cf_name].append(key)

    # Scan all service directories for PropertyType files
    for entry in resources_dir.iterdir():
        if entry.name.startswith("_") or not entry.is_dir():
            continue

        service_name = entry.name

        # Scan submodules (e.g., s3/bucket.py contains PropertyTypes for Bucket)
        for py_file in entry.glob("*.py"):
            if py_file.name.startswith("_") or py_file.name == "__init__.py":
                continue
            # Module name for PropertyTypes: "s3.bucket"
            module_name = f"{service_name}.{py_file.stem}"
            process_file(py_file, module_name)


def get_property_type_info(module: str, class_name: str) -> dict[str, Any] | None:
    """Get information about a PropertyType class.

    Args:
        module: Module name (e.g., "s3.bucket")
        class_name: Class name (e.g., "BucketEncryption")

    Returns:
        Dict with cf_to_python, python_to_cf, and field_types mappings,
        or None if not found.
    """
    _build_property_type_map()
    return _PROPERTY_TYPE_MAP.get((module, class_name)) if _PROPERTY_TYPE_MAP else None


def find_property_type_for_cf_keys(
    cf_keys: set[str], module_hint: str | None = None
) -> tuple[str, str] | None:
    """Find a PropertyType class that matches a set of CloudFormation property keys.

    Uses case-insensitive matching to handle acronym variations like TTL/Ttl.

    Args:
        cf_keys: Set of CloudFormation property names from a dict
        module_hint: Optional module prefix to prefer (e.g., "s3").

    Returns:
        Tuple of (module_name, class_name) or None if no match.
    """
    _build_property_type_map()

    if not _PROPERTY_TYPE_MAP or not _CF_PROPERTY_TO_CLASSES:
        return None

    # Normalize keys to lowercase for case-insensitive matching
    cf_keys_lower = {k.lower() for k in cf_keys}

    # Find candidates that have at least one matching key (case-insensitive)
    candidates: dict[tuple[str, str], int] = {}
    for key in cf_keys:
        # Try exact match first
        if key in _CF_PROPERTY_TO_CLASSES:
            for class_key in _CF_PROPERTY_TO_CLASSES[key]:
                if module_hint and not class_key[0].startswith(module_hint):
                    continue
                candidates[class_key] = candidates.get(class_key, 0) + 1
        else:
            # Try case-insensitive match
            for cf_key in _CF_PROPERTY_TO_CLASSES:
                if cf_key.lower() == key.lower():
                    for class_key in _CF_PROPERTY_TO_CLASSES[cf_key]:
                        if module_hint and not class_key[0].startswith(module_hint):
                            continue
                        candidates[class_key] = candidates.get(class_key, 0) + 1

    if not candidates:
        return None

    # Score candidates: prefer classes where ALL provided keys are valid
    best_matches: list[tuple[tuple[str, str], float, int]] = []
    for class_key, match_count in candidates.items():
        info = _PROPERTY_TYPE_MAP[class_key]
        total_keys = len(info["cf_to_python"])
        # Build lowercase version of expected keys for case-insensitive comparison
        expected_keys_lower = {k.lower() for k in info["cf_to_python"].keys()}

        # Check if all provided keys are in the expected set (case-insensitive)
        if not cf_keys_lower.issubset(expected_keys_lower):
            continue

        # Score: ratio of matched keys to total keys (higher = more specific)
        specificity = match_count / total_keys if total_keys > 0 else 0
        best_matches.append((class_key, specificity, total_keys))

    if not best_matches:
        return None

    # Sort by specificity desc (prefer more specific matches)
    best_matches.sort(key=lambda x: (-x[1], x[2]))
    return best_matches[0][0]


def resolve_property_type(
    expected_class: str | None,
    expected_module: str | None,
    cf_keys: set[str],
    module_hint: str | None = None,
) -> tuple[str, str, dict[str, Any]] | None:
    """Resolve a PropertyType from expected type or CF keys.

    Args:
        expected_class: Expected class name from type hint (e.g., "BucketEncryption")
        expected_module: Module from parent resource (e.g., "s3")
        cf_keys: Set of CloudFormation property names from the dict
        module_hint: Optional module hint for ambiguous cases

    Returns:
        Tuple of (module_name, class_name, info_dict) or None if not found.
    """
    _build_property_type_map()

    if not _PROPERTY_TYPE_MAP:
        return None

    # Strategy 1: Direct lookup if we have expected class and module
    if expected_class and expected_module:
        # Try nested module first: s3.bucket.BucketEncryption
        for key in _PROPERTY_TYPE_MAP:
            if key[0].startswith(expected_module) and key[1] == expected_class:
                return (key[0], key[1], _PROPERTY_TYPE_MAP[key])

    # Strategy 2: Find by CF keys
    hint = module_hint or (expected_module.split(".")[0] if expected_module else None)
    match = find_property_type_for_cf_keys(cf_keys, hint)
    if match:
        return (match[0], match[1], _PROPERTY_TYPE_MAP[match])

    return None


def extract_class_from_type_hint(type_hint: str | None) -> str | None:
    """Extract class name from a type hint string.

    Examples:
        "Optional[BucketEncryption]" -> "BucketEncryption"
        "list[ServerSideEncryptionRule]" -> "ServerSideEncryptionRule"
        "BucketEncryption | None" -> "BucketEncryption"
    """
    if not type_hint:
        return None

    import re

    # Remove Optional[], list[], Union[], and | None
    cleaned = type_hint.replace(" | None", "").replace("| None", "")
    # Match class name inside Optional[], list[], etc.
    match = re.search(r"(?:Optional|list|List)\[(\w+)\]", cleaned)
    if match:
        return match.group(1)
    # Match bare class name
    match = re.search(r"^(\w+)$", cleaned.strip())
    if match:
        return match.group(1)
    return None
