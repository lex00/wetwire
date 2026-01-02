"""Enum constant lookup for the importer.

Provides functions to look up typed enum constants for property values,
enabling the importer to generate code like:

    runtime = lambda_.RuntimePython312

Instead of:

    runtime = "python3.12"
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .context import CodegenContext

# Mapping from CloudFormation property name to botocore enum shape name.
# Property names are snake_case as used in generated Python code.
# This handles cases where the CloudFormation property name differs from
# the botocore enum type name.
PROPERTY_ENUM_MAPPINGS: dict[str, dict[str, str]] = {
    "lambda": {
        "runtime": "Runtime",
        "package_type": "PackageType",
        "architectures": "Architecture",  # Note: plural in CF, singular in botocore
    },
    "ec2": {
        "volume_type": "VolumeType",
    },
    "ecs": {
        "launch_type": "LaunchType",
        "scheduling_strategy": "SchedulingStrategy",
        "network_mode": "NetworkMode",
    },
    "s3": {
        "storage_class": "StorageClass",
        "access_control": "BucketCannedACL",
        "sse_algorithm": "ServerSideEncryption",
        "mode": "ObjectLockRetentionMode",
        "status": "BucketVersioningStatus",
    },
    "dynamodb": {
        "billing_mode": "BillingMode",
        "stream_view_type": "StreamViewType",
        "table_class": "TableClass",
    },
    "apigateway": {
        "integration_type": "IntegrationType",
    },
    "elasticloadbalancingv2": {
        "protocol": "ProtocolEnum",
        "target_type": "TargetTypeEnum",
    },
    "logs": {
        "log_group_class": "LogGroupClass",
    },
    "certificatemanager": {
        "validation_method": "ValidationMethod",
    },
    "events": {
        "state": "RuleState",
    },
}

# Mapping from CloudFormation service names to botocore service names
CF_TO_BOTOCORE_SERVICE = {
    "lambda_": "lambda",
    "certificatemanager": "acm",
    "elasticloadbalancingv2": "elbv2",
}


@lru_cache(maxsize=1)
def _load_enums() -> dict[str, dict[str, dict[str, dict[str, list[dict[str, str]]]]]]:
    """Load the enums.json file.

    Returns the enums data structure with schema:
    {services: {service: {enumName: {name: str, values: [{name, value}]}}}}
    """
    # Find specs directory relative to this file
    # src/wetwire_aws/importer/codegen/enum_lookup.py -> specs/enums.json
    this_file = Path(__file__)
    specs_dir = this_file.parent.parent.parent.parent.parent / "specs"
    enums_path = specs_dir / "enums.json"

    if not enums_path.exists():
        return {"services": {}}

    result: dict[str, dict[str, dict[str, dict[str, list[dict[str, str]]]]]] = (
        json.loads(enums_path.read_text())
    )
    return result


def _get_enum_values(botocore_service: str, enum_name: str) -> dict[str, str] | None:
    """Get a mapping of value -> constant_name for an enum.

    Returns None if the service/enum is not found.
    """
    enums = _load_enums()
    service_enums = enums.get("services", {}).get(botocore_service, {})
    enum_def = service_enums.get(enum_name)

    if not enum_def:
        return None

    # Build value -> constant_name mapping
    return {v["value"]: v["name"] for v in enum_def.get("values", [])}


def try_enum_constant(
    ctx: CodegenContext,
    property_name: str,
    value: str,
    service_module: str | None = None,
) -> str | None:
    """Try to convert a string value to an enum constant reference.

    Args:
        ctx: Code generation context (provides current resource type info)
        property_name: The snake_case property name (e.g., "runtime")
        value: The string value (e.g., "python3.12")
        service_module: Optional service module name override (e.g., "lambda_", "s3")

    Returns:
        Enum constant reference string (e.g., "lambda_.RuntimePython312") or None
        if no enum mapping exists for this property/value combination.
    """
    # Get the CloudFormation service name from context or parameter
    cf_service = service_module or ctx.current_module
    if not cf_service:
        return None

    # Normalize service name (strip trailing underscore for Python keywords like lambda_)
    cf_service_lower = cf_service.lower().rstrip("_")

    # Check if we have an enum mapping for this property
    service_mappings = PROPERTY_ENUM_MAPPINGS.get(cf_service_lower, {})
    enum_name = service_mappings.get(property_name)

    if not enum_name:
        return None

    # Get the botocore service name
    botocore_service = CF_TO_BOTOCORE_SERVICE.get(cf_service_lower, cf_service_lower)

    # Look up the enum values
    enum_values = _get_enum_values(botocore_service, enum_name)
    if not enum_values:
        return None

    # Check if our value is in the enum
    const_name = enum_values.get(value)
    if not const_name:
        return None

    # Generate the module-qualified constant reference
    # e.g., lambda_.Runtime.PYTHON3_12
    module_name = cf_service_lower
    if module_name == "lambda":
        module_name = "lambda_"  # Python keyword

    # Add import for the module
    ctx.add_import("wetwire_aws.resources", module_name)

    # Return the qualified constant reference: module.EnumClass.CONST_NAME
    return f"{module_name}.{enum_name}.{const_name}"
