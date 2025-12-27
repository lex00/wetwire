"""
Extract enum values from botocore service models.

This module extracts enum types from botocore to provide type-safe constants
for CloudFormation properties (e.g., Runtime.PYTHON3_12).

Usage:
    python -m codegen.extract_enums
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from codegen.config import SPECS_DIR

# Mapping from CloudFormation service names to botocore service names
# CloudFormation uses different service names than botocore in some cases
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
    "elasticloadbalancing": "elb",
    "elasticloadbalancingv2": "elbv2",
    "events": "events",
    "iam": "iam",
    "kinesis": "kinesis",
    "kms": "kms",
    "logs": "logs",
    "rds": "rds",
    "redshift": "redshift",
    "route53": "route53",
    "s3": "s3",
    "secretsmanager": "secretsmanager",
    "ses": "ses",
    "sns": "sns",
    "sqs": "sqs",
    "ssm": "ssm",
    "stepfunctions": "stepfunctions",
    "wafv2": "wafv2",
}


# Known enum mappings: (service, property_pattern) -> botocore_shape_name
# This handles cases where the shape name doesn't match the property name
KNOWN_ENUM_MAPPINGS = {
    ("lambda", "runtime"): "Runtime",
    ("lambda", "architecture"): "Architecture",
    ("lambda", "package_type"): "PackageType",
    ("dynamodb", "billing_mode"): "BillingMode",
    ("dynamodb", "stream_view_type"): "StreamViewType",
    ("dynamodb", "table_class"): "TableClass",
    ("ec2", "instance_type"): "InstanceType",
    ("s3", "access_control"): "BucketCannedACL",
    ("rds", "engine"): "String",  # Not an enum in botocore
}


def get_botocore_service(cf_service: str) -> str:
    """Get the botocore service name for a CloudFormation service."""
    return CF_TO_BOTOCORE_SERVICE.get(cf_service, cf_service)


def to_python_enum_name(value: str) -> str:
    """
    Convert an enum value to a valid Python identifier.

    Examples:
        "python3.12" -> "PYTHON3_12"
        "PAY_PER_REQUEST" -> "PAY_PER_REQUEST"
        "t2.micro" -> "T2_MICRO"
    """
    # Replace dots and hyphens with underscores
    name = value.replace(".", "_").replace("-", "_")
    # Remove any other non-alphanumeric characters
    name = re.sub(r"[^a-zA-Z0-9_]", "", name)
    # Convert to uppercase
    name = name.upper()
    # Ensure it starts with a letter or underscore
    if name and name[0].isdigit():
        name = "_" + name
    return name


def extract_all_enums() -> dict[str, dict[str, list[str]]]:
    """
    Extract all enums from botocore for all available services.

    Returns:
        Dict mapping service -> shape_name -> list of enum values
    """
    try:
        import botocore.loaders
        import botocore.session
    except ImportError:
        print("botocore not installed, skipping enum extraction")
        return {}

    loader = botocore.loaders.Loader()
    session = botocore.session.get_session()

    # Get list of available services
    available_services = session.get_available_services()

    result: dict[str, dict[str, list[str]]] = defaultdict(dict)

    for service_name in available_services:
        try:
            service_model = loader.load_service_model(service_name, "service-2")
            shapes = service_model.get("shapes", {})

            for shape_name, shape_def in shapes.items():
                if shape_def.get("type") == "string" and "enum" in shape_def:
                    enum_values = shape_def["enum"]
                    # Filter out very large enums (likely not useful as constants)
                    if len(enum_values) <= 200:
                        result[service_name][shape_name] = enum_values

        except Exception:
            # Service might not have service-2 model
            continue

    return dict(result)


def extract_enums_for_services(services: list[str]) -> dict[str, dict[str, list[str]]]:
    """
    Extract enums from botocore for specific services.

    Args:
        services: List of CloudFormation service names

    Returns:
        Dict mapping cf_service -> shape_name -> list of enum values
    """
    try:
        import botocore.loaders
    except ImportError:
        print("botocore not installed, skipping enum extraction")
        return {}

    loader = botocore.loaders.Loader()
    result: dict[str, dict[str, list[str]]] = {}

    for cf_service in services:
        botocore_service = get_botocore_service(cf_service)

        try:
            service_model = loader.load_service_model(botocore_service, "service-2")
            shapes = service_model.get("shapes", {})

            service_enums: dict[str, list[str]] = {}

            for shape_name, shape_def in shapes.items():
                if shape_def.get("type") == "string" and "enum" in shape_def:
                    enum_values = shape_def["enum"]
                    # Filter out very large enums
                    if len(enum_values) <= 200:
                        service_enums[shape_name] = enum_values

            if service_enums:
                result[cf_service] = service_enums

        except Exception as e:
            print(f"  Warning: Could not load enums for {cf_service}: {e}")
            continue

    return result


def generate_enum_class(enum_name: str, values: list[str]) -> dict:
    """
    Generate enum definition for the intermediate schema.

    Returns dict with enum name and values ready for code generation.
    """
    return {
        "name": enum_name,
        "values": [
            {"name": to_python_enum_name(v), "value": v}
            for v in values
            if to_python_enum_name(v)  # Filter out empty names
        ],
    }


def extract_and_save(output_path: Path | None = None) -> dict:
    """
    Extract all enums and save to JSON.

    Args:
        output_path: Where to save the enums.json file

    Returns:
        The extracted enum data
    """
    print("Extracting enums from botocore...")

    all_enums = extract_all_enums()

    # Count totals
    total_services = len(all_enums)
    total_enums = sum(len(shapes) for shapes in all_enums.values())
    total_values = sum(
        len(values) for shapes in all_enums.values() for values in shapes.values()
    )

    print(f"  Found {total_enums} enum types across {total_services} services")
    print(f"  Total {total_values} enum values")

    # Prepare output
    output = {"services": {}}

    for service, shapes in sorted(all_enums.items()):
        output["services"][service] = {
            shape_name: generate_enum_class(shape_name, values)
            for shape_name, values in sorted(shapes.items())
        }

    # Save to file
    if output_path is None:
        output_path = SPECS_DIR / "enums.json"

    output_path.write_text(json.dumps(output, indent=2))
    print(f"\nEnums written to {output_path}")

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Extract enum values from botocore service models"
    )
    parser.add_argument(
        "--output", type=Path, help="Output file path (default: specs/enums.json)"
    )
    parser.add_argument(
        "--services",
        nargs="+",
        help="Only extract for specific services (CloudFormation names)",
    )
    args = parser.parse_args()

    try:
        if args.services:
            enums = extract_enums_for_services(args.services)
            output = {
                "services": {
                    s: {n: generate_enum_class(n, v) for n, v in shapes.items()}
                    for s, shapes in enums.items()
                }
            }
            output_path = args.output or SPECS_DIR / "enums.json"
            output_path.write_text(json.dumps(output, indent=2))
            print(f"Enums written to {output_path}")
        else:
            extract_and_save(args.output)
        print("\nEnum extraction completed successfully!")
    except Exception as e:
        print(f"\nEnum extraction failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
