"""
Stage 3: Generate Python dataclasses from intermediate format.

Reads the parsed intermediate schema and generates Python source files
for each AWS service, including enum constants from botocore.

Structure:
    Each AWS service becomes a package (e.g., dynamodb/) containing:
    - __init__.py: Resource classes, enums, and submodule imports
    - {Resource}.py: PropertyTypes for each resource (e.g., Table.py)

    This mirrors CloudFormation's type hierarchy:
    - AWS::DynamoDB::Table -> dynamodb.Table
    - AWS::DynamoDB::Table.AttributeDefinition -> dynamodb.Table.AttributeDefinition
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from codegen.config import GENERATOR_VERSION, RESOURCES_DIR, SPECS_DIR
from codegen.schema import (
    IntermediateSchema,
    NestedTypeDef,
    PropertyDef,
    ResourceDef,
    python_type_for_property,
)

# Use all available CPU cores for parallel generation
NUM_WORKERS = os.cpu_count() or 4


# Mapping from CloudFormation service names to botocore service names
CF_TO_BOTOCORE_SERVICE = {
    "lambda_": "lambda",
    "apigateway": "apigateway",
    "apigatewayv2": "apigatewayv2",
    "applicationautoscaling": "application-autoscaling",
    "autoscaling": "autoscaling",
    "certificatemanager": "acm",
    "cloudfront": "cloudfront",
    "cloudwatch": "cloudwatch",
    "codebuild": "codebuild",
    "codepipeline": "codepipeline",
    "cognito": "cognito-idp",
    "dynamodb": "dynamodb",
    "ec2": "ec2",
    "ecr": "ecr",
    "ecs": "ecs",
    "efs": "efs",
    "elasticache": "elasticache",
    "elasticbeanstalk": "elasticbeanstalk",
    "elasticloadbalancingv2": "elbv2",
    "elasticloadbalancing": "elb",
    "elasticsearch": "es",
    "emr": "emr",
    "events": "events",
    "evidently": "evidently",
    "fis": "fis",
    "frauddetector": "frauddetector",
    "fsx": "fsx",
    "gamelift": "gamelift",
    "globalaccelerator": "globalaccelerator",
    "glue": "glue",
    "greengrass": "greengrass",
    "greengrassv2": "greengrassv2",
    "guardduty": "guardduty",
    "iam": "iam",
    "imagebuilder": "imagebuilder",
    "inspector": "inspector",
    "iot": "iot",
    "iotanalytics": "iotanalytics",
    "iotevents": "iotevents",
    "iotsitewise": "iotsitewise",
    "iotwireless": "iotwireless",
    "kafka": "kafka",
    "kendra": "kendra",
    "kinesis": "kinesis",
    "kinesisanalytics": "kinesisanalytics",
    "kinesisanalyticsv2": "kinesisanalyticsv2",
    "kinesisfirehose": "firehose",
    "kms": "kms",
    "lakeformation": "lakeformation",
    "lambda_": "lambda",
    "lex": "lex-models",
    "lightsail": "lightsail",
    "logs": "logs",
    "macie": "macie2",
    "mediaconnect": "mediaconnect",
    "mediaconvert": "mediaconvert",
    "medialive": "medialive",
    "mediapackage": "mediapackage",
    "mediastore": "mediastore",
    "memorydb": "memorydb",
    "msk": "kafka",
    "mwaa": "mwaa",
    "neptune": "neptune",
    "networkfirewall": "network-firewall",
    "networkmanager": "networkmanager",
    "opensearchservice": "opensearch",
    "opsworks": "opsworks",
    "pinpoint": "pinpoint",
    "qldb": "qldb",
    "quicksight": "quicksight",
    "rds": "rds",
    "redshift": "redshift",
    "rekognition": "rekognition",
    "resiliencehub": "resiliencehub",
    "resourcegroups": "resource-groups",
    "robomaker": "robomaker",
    "route53": "route53",
    "route53resolver": "route53resolver",
    "s3": "s3",
    "sagemaker": "sagemaker",
    "scheduler": "scheduler",
    "secretsmanager": "secretsmanager",
    "securityhub": "securityhub",
    "servicecatalog": "servicecatalog",
    "servicediscovery": "servicediscovery",
    "ses": "ses",
    "sns": "sns",
    "sqs": "sqs",
    "ssm": "ssm",
    "stepfunctions": "stepfunctions",
    "synthetics": "synthetics",
    "timestream": "timestream-write",
    "transfer": "transfer",
    "waf": "waf",
    "wafregional": "waf-regional",
    "wafv2": "wafv2",
    "workspaces": "workspaces",
    "xray": "xray",
}


def to_snake_case(name: str) -> str:
    """Convert PascalCase to snake_case."""
    import re
    # Handle consecutive capitals (e.g., EC2Fleet -> ec2_fleet)
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def generate_enum_class(name: str, enum_data: dict) -> str:
    """Generate an enum-like class with string constants."""
    lines = [f"class {name}:"]

    values = enum_data.get("values", [])
    if not values:
        lines.append("    pass")
        return "\n".join(lines)

    for val in values:
        const_name = val["name"]
        value = val["value"]
        # Escape quotes in value
        escaped_value = value.replace('"', '\\"')
        lines.append(f'    {const_name} = "{escaped_value}"')

    return "\n".join(lines)


def load_enums_for_service(service: str) -> dict[str, dict]:
    """Load enum definitions for a service from enums.json."""
    enums_path = SPECS_DIR / "enums.json"
    if not enums_path.exists():
        return {}

    try:
        all_enums = json.loads(enums_path.read_text())
        services = all_enums.get("services", {})

        # Try direct match first
        if service in services:
            return services[service]

        # Try botocore service name mapping
        botocore_name = CF_TO_BOTOCORE_SERVICE.get(service, service)
        if botocore_name in services:
            return services[botocore_name]

        return {}
    except Exception:
        return {}


def get_all_enums_for_service(
    service: str, all_enums: dict[str, dict]
) -> list[tuple[str, dict]]:
    """Get all enums for a service."""
    return [(name, data) for name, data in sorted(all_enums.items())]


def generate_property_type_file_header(resource_type: str) -> str:
    """Generate header for a PropertyType submodule file."""
    return f'''"""PropertyTypes for {resource_type}."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from wetwire_aws.base import PropertyType, Tag

'''


def generate_init_file_header(
    service: str,
    cf_spec_version: str,
    generator_version: str,
) -> str:
    """Generate header for the service __init__.py file."""
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f'''"""
AWS {service.upper()} CloudFormation resources.

Generated:
  Source: CloudFormation Spec {cf_spec_version}
  Generator: {generator_version}
  Date: {timestamp}

DO NOT EDIT - This file is generated by wetwire-aws codegen.
To regenerate: python -m wetwire_aws.codegen.generate
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from wetwire_aws.base import CloudFormationResource, PropertyType, Tag

'''


def _needs_property_mapping(prop: PropertyDef) -> bool:
    """Check if a property needs explicit mapping (won't round-trip via simple conversion).

    CloudFormation uses PascalCase with uppercase acronyms (SSEAlgorithm, KMSKeyId, VPCId).
    Our to_snake_case converts these correctly, but _to_cf_name's simple capitalize()
    produces SseAlgorithm instead of SSEAlgorithm.

    Args:
        prop: Property definition with name (snake_case) and original_name (CloudFormation).

    Returns:
        True if the property needs an explicit mapping.
    """
    # Convert snake_case back to PascalCase using the same algorithm as _to_cf_name
    snake_name = prop.name
    if snake_name.endswith("_") and not snake_name.endswith("__"):
        snake_name = snake_name[:-1]
    reconstructed = "".join(word.capitalize() for word in snake_name.split("_"))
    return reconstructed != prop.original_name


def generate_property_type_class(
    nested: NestedTypeDef,
    class_name: str | None = None,
) -> str:
    """Generate a PropertyType class for a nested structure.

    Within a submodule, all types are in the same namespace, so no qualified refs needed.
    """
    # Reserved names that conflict with imports
    RESERVED_NAMES = {"PropertyType", "Tag"}

    lines = []
    name = class_name if class_name else nested.name

    # Rename classes that conflict with imports
    if name in RESERVED_NAMES:
        name = f"{name}Definition"

    lines.append("@dataclass")
    lines.append(f"class {name}(PropertyType):")

    if not nested.properties:
        lines.append("    pass")
        return "\n".join(lines)

    # Check for properties that need explicit mappings
    property_mappings = {
        prop.name: prop.original_name
        for prop in nested.properties
        if _needs_property_mapping(prop)
    }

    if property_mappings:
        # Generate _property_mappings class variable
        lines.append("    _property_mappings: ClassVar[dict[str, str]] = {")
        for py_name, cf_name in sorted(property_mappings.items()):
            lines.append(f'        "{py_name}": "{cf_name}",')
        lines.append("    }")
        lines.append("")

    for prop in nested.properties:
        python_type = python_type_for_property(prop)

        # All fields are optional to avoid dataclass inheritance issues
        if python_type.startswith("list"):
            lines.append(
                f"    {prop.name}: {python_type} = field(default_factory=list)"
            )
        elif python_type.startswith("dict") and not python_type.startswith(
            "dict[str, Any]"
        ):
            lines.append(
                f"    {prop.name}: {python_type} = field(default_factory=dict)"
            )
        else:
            lines.append(f"    {prop.name}: {python_type} | None = None")

    return "\n".join(lines)


def generate_resource_class(
    resource: ResourceDef,
    submodule_name: str | None = None,
) -> str:
    """Generate a CloudFormationResource class.

    If submodule_name is provided, property types are referenced via that submodule.
    """
    # Reserved names that conflict with imports
    RESERVED_NAMES = {"PropertyType", "Tag", "CloudFormationResource"}

    lines = []
    class_name = resource.name

    # Rename classes that conflict with imports
    if class_name in RESERVED_NAMES:
        class_name = f"{class_name}Resource"

    lines.append("@dataclass")
    lines.append(f"class {class_name}(CloudFormationResource):")

    # Docstring
    doc_lines = [f'"""{resource.name} resource.']
    if resource.documentation:
        doc_lines.append("")
        doc_lines.append(resource.documentation)
    doc_lines.append("")
    doc_lines.append(f"CloudFormation type: {resource.full_type}")
    doc_lines.append('"""')
    lines.append("    " + "\n    ".join(doc_lines))
    lines.append("")

    # Class variables
    lines.append(f'    _resource_type: ClassVar[str] = "{resource.full_type}"')

    if not resource.properties:
        lines.append("")
        lines.append("    pass")
        return "\n".join(lines)

    # Check for properties that need explicit mappings
    property_mappings = {
        prop.name: prop.original_name
        for prop in resource.properties
        if _needs_property_mapping(prop)
    }

    if property_mappings:
        lines.append("    _property_mappings: ClassVar[dict[str, str]] = {")
        for py_name, cf_name in sorted(property_mappings.items()):
            lines.append(f'        "{py_name}": "{cf_name}",')
        lines.append("    }")
    lines.append("")

    # Generate properties
    for prop in resource.properties:
        python_type = python_type_for_property(prop)
        field_name = prop.name

        # If we have a nested type and a submodule, qualify the reference
        # Exception: Tag is imported from base, so use it directly
        if prop.nested_type and submodule_name:
            if prop.nested_type == "Tag":
                # Tag is imported from base, not from submodule
                type_name = "Tag"
            else:
                type_name = f"{submodule_name}.{prop.nested_type}"
            if prop.is_list:
                python_type = f"list[{type_name}]"
            elif prop.is_map:
                python_type = f"dict[str, {type_name}]"
            else:
                python_type = type_name

        # All fields are optional to avoid dataclass inheritance issues
        if python_type.startswith("list"):
            lines.append(
                f"    {field_name}: {python_type} = field(default_factory=list)"
            )
        elif python_type.startswith("dict") and not python_type.startswith(
            "dict[str, Any]"
        ):
            lines.append(
                f"    {field_name}: {python_type} = field(default_factory=dict)"
            )
        else:
            lines.append(f"    {field_name}: {python_type} | None = None")

    # Generate attribute accessors if there are attributes
    if resource.attributes:
        lines.append("")
        lines.append("    # GetAtt attributes")
        for attr in resource.attributes:
            attr_const = attr.name.upper().replace("-", "_").replace(".", "_")
            lines.append(f'    {attr_const}: ClassVar[str] = "{attr.name}"')

    return "\n".join(lines)


def generate_property_type_module(
    resource: ResourceDef,
    nested_types: list[NestedTypeDef],
) -> str:
    """Generate a PropertyType submodule for a single resource."""
    lines = [generate_property_type_file_header(resource.full_type)]

    for nested in sorted(nested_types, key=lambda n: n.name):
        lines.append("")
        lines.append(generate_property_type_class(nested))

    return "\n".join(lines)


def generate_service_package(
    service: str,
    resources: list[ResourceDef],
    nested_types: list[NestedTypeDef],
    cf_spec_version: str,
    service_enums: list[tuple[str, dict]] | None = None,
    output_dir: Path | None = None,
) -> dict[str, str]:
    """
    Generate a service package with submodules for PropertyTypes.

    Returns a dict of {filename: content} for all files to be written.
    """
    output_dir = output_dir or RESOURCES_DIR
    package_dir = output_dir / service

    files: dict[str, str] = {}

    # Group nested types by their parent resource
    # original_name format: "AWS::DynamoDB::Table.AttributeDefinition"
    nested_by_resource: dict[str, list[NestedTypeDef]] = defaultdict(list)
    for nested in nested_types:
        if "." in nested.original_name:
            # Extract resource name: "AWS::DynamoDB::Table" -> "Table"
            resource_part = nested.original_name.split(".")[0]
            resource_name = resource_part.split("::")[-1]
            nested_by_resource[resource_name].append(nested)

    # Track which resources have submodules
    submodules: list[str] = []
    resource_names = {r.name for r in resources}

    # Generate PropertyType submodules for each resource
    # Use PascalCase to match CloudFormation spec naming (e.g., SecurityGroup.Ingress)
    for resource in resources:
        resource_nested = nested_by_resource.get(resource.name, [])
        if resource_nested:
            submodule_name = resource.name  # Keep PascalCase
            submodules.append(submodule_name)

            content = generate_property_type_module(resource, resource_nested)
            files[f"{service}/{submodule_name}.py"] = content

    # Build resource -> submodule mapping (with underscore prefix for the alias)
    resource_submodule_map: dict[str, str] = {}
    for resource in resources:
        if resource.name in nested_by_resource:
            resource_submodule_map[resource.name] = "_" + resource.name  # Keep PascalCase

    # Generate __init__.py
    init_lines = [generate_init_file_header(service, cf_spec_version, GENERATOR_VERSION)]

    # Generate enum constants
    reserved_enum_names = {"PropertyType", "Tag", "CloudFormationResource", "Any", "ClassVar"}

    if service_enums:
        init_lines.append("# Constants")
        init_lines.append("# " + "=" * 60)

        for enum_name, enum_data in sorted(service_enums, key=lambda x: x[0]):
            # Rename enums that conflict with imports or resources
            actual_name = enum_name
            if enum_name in reserved_enum_names or enum_name in resource_names:
                actual_name = f"{enum_name}Values"
            init_lines.append("")
            init_lines.append(generate_enum_class(actual_name, enum_data))
        init_lines.append("")

    # Add submodule imports with alias to avoid shadowing by field names
    # e.g., "from . import table as _table" so _table.AttributeDefinition doesn't
    # get shadowed when a resource has a field named "table"
    if submodules:
        init_lines.append("")
        init_lines.append("")
        init_lines.append("# PropertyType submodules")
        for submod in sorted(set(submodules)):
            init_lines.append(f"from . import {submod} as _{submod}")

    # Generate resource classes
    init_lines.append("")
    init_lines.append("")
    init_lines.append("# Resources")
    init_lines.append("# " + "=" * 60)

    for resource in sorted(resources, key=lambda r: r.name):
        submodule = resource_submodule_map.get(resource.name)
        init_lines.append("")
        init_lines.append(generate_resource_class(resource, submodule))

    # Attach PropertyTypes to resource classes so s3.Bucket.BucketEncryption works
    # This allows users to write: resource: s3.Bucket.BucketEncryption
    if submodules:
        init_lines.append("")
        init_lines.append("")
        init_lines.append("# Attach PropertyTypes to resource classes for convenient access")
        init_lines.append("# e.g., s3.Bucket.BucketEncryption instead of s3._Bucket.BucketEncryption")
        for resource in sorted(resources, key=lambda r: r.name):
            if resource.name in nested_by_resource:
                resource_nested = nested_by_resource[resource.name]
                for nested in sorted(resource_nested, key=lambda n: n.name):
                    # Attach each PropertyType class to the resource class
                    init_lines.append(f"{resource.name}.{nested.name} = _{resource.name}.{nested.name}")

    init_lines.append("")

    files[f"{service}/__init__.py"] = "\n".join(init_lines)

    return files


def generate_resources_init_file(services: list[str], cf_spec_version: str) -> str:
    """Generate the resources/__init__.py file."""
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        '"""',
        "AWS CloudFormation resource types.",
        "",
        "Generated:",
        f"  Source: CloudFormation Spec {cf_spec_version}",
        f"  Generator: {GENERATOR_VERSION}",
        f"  Date: {timestamp}",
        "",
        "DO NOT EDIT - This file is generated by wetwire-aws codegen.",
        "To regenerate: python -m wetwire_aws.codegen.generate",
        '"""',
        "",
        "# Service packages are imported on demand to avoid loading all resources",
        "# Usage: from wetwire_aws.resources import s3, dynamodb",
        "",
    ]

    # Add __all__ for explicit imports
    lines.append("__all__ = [")
    for service in sorted(services):
        lines.append(f'    "{service}",')
    lines.append("]")

    return "\n".join(lines)


def write_service_package(
    service: str,
    resources: list[ResourceDef],
    nested_types: list[NestedTypeDef],
    cf_spec_version: str,
) -> int:
    """Write a service package to disk. Returns number of files written."""
    # Load enums for this service
    all_enums = load_enums_for_service(service)
    service_enums = get_all_enums_for_service(service, all_enums) if all_enums else None

    # Generate all files for this service
    files = generate_service_package(
        service, resources, nested_types, cf_spec_version, service_enums
    )

    # Create package directory
    package_dir = RESOURCES_DIR / service
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)

    # Write files
    for filename, content in files.items():
        filepath = RESOURCES_DIR / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content + "\n")

    return len(files)


def main():
    """Generate Python resource classes from parsed CloudFormation spec."""
    parser = argparse.ArgumentParser(description="Generate Python CloudFormation resources")
    parser.add_argument("--input", default=SPECS_DIR / "parsed.json", help="Input parsed schema file")
    parser.add_argument("--output", default=RESOURCES_DIR, help="Output directory")
    parser.add_argument("--service", help="Generate only this service")
    args = parser.parse_args()

    print("Stage 3: Generate")
    print("=" * 40)

    # Load parsed schema
    input_path = Path(args.input)
    print(f"Loading {input_path}...")
    data = json.loads(input_path.read_text())
    schema = IntermediateSchema.from_dict(data)

    # Group by service
    resources_by_service: dict[str, list[ResourceDef]] = defaultdict(list)
    nested_by_service: dict[str, list[NestedTypeDef]] = defaultdict(list)

    for resource in schema.resources:
        resources_by_service[resource.service].append(resource)
    for nested in schema.nested_types:
        nested_by_service[nested.service].append(nested)

    services = sorted(resources_by_service.keys())
    if args.service:
        if args.service not in services:
            print(f"Error: Service '{args.service}' not found")
            sys.exit(1)
        services = [args.service]

    print(f"Generating {len(services)} service modules...")

    # Load enum constants
    print("Loading enum constants from botocore...")

    # Clean output directory (except __init__.py)
    output_dir = Path(args.output)
    if output_dir.exists() and not args.service:
        for item in output_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate services in parallel
    total_files = 0
    total_enums = 0

    def process_service(service: str) -> tuple[str, int, int]:
        resources = resources_by_service[service]
        nested = nested_by_service.get(service, [])

        # Load enums
        all_enums = load_enums_for_service(service)
        enum_count = len(all_enums)

        file_count = write_service_package(
            service, resources, nested, schema.source_version
        )

        print(
            f"  {service}: {len(resources)} resources, {len(nested)} property types"
            + (f", {enum_count} enums" if enum_count else "")
        )

        return service, file_count, enum_count

    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {executor.submit(process_service, s): s for s in services}
        for future in as_completed(futures):
            service, file_count, enum_count = future.result()
            total_files += file_count
            total_enums += enum_count

    # Generate resources/__init__.py
    init_content = generate_resources_init_file(services, schema.source_version)
    (output_dir / "__init__.py").write_text(init_content + "\n")
    total_files += 1

    print(f"\nGenerated {total_files} files")
    print(f"  Including {total_enums} enum constant classes")

    # Format with ruff (optional - skip if not installed)
    if shutil.which("ruff"):
        print("\nFormatting with ruff...")
        result = subprocess.run(
            ["ruff", "format", str(output_dir), "--quiet"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"  Formatted {total_files}/{total_files} files")
        else:
            print(f"  Warning: ruff formatting failed: {result.stderr}")
    else:
        print("\nSkipping ruff formatting (not installed)")

    print(f"\nOutput written to {output_dir}")
    print("\nGenerate completed successfully!")


if __name__ == "__main__":
    main()
