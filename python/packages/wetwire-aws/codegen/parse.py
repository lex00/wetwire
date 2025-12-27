"""
Stage 2: Parse source materials into intermediate format.

Reads the CloudFormation spec and botocore service models,
transforms them into a normalized intermediate schema.
"""

import argparse
import json
import re
import sys
from datetime import UTC, datetime

from codegen.config import PYTHON_KEYWORDS, SPECS_DIR
from codegen.intermediate import (
    AttributeDef,
    IntermediateSchema,
    NestedTypeDef,
    PropertyDef,
    ResourceDef,
)


def to_snake_case(name: str) -> str:
    """Convert PascalCase or camelCase to snake_case."""
    # Handle acronyms (e.g., VPCId -> vpc_id, not v_p_c_id)
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    result = s2.lower()

    # Handle Python keywords
    if result in PYTHON_KEYWORDS:
        result = PYTHON_KEYWORDS[result]

    return result


def to_class_name(name: str) -> str:
    """Convert a name to a valid Python class name."""
    # Remove any non-alphanumeric characters
    name = re.sub(r"[^a-zA-Z0-9]", "", name)
    return name


def parse_cf_type(
    cf_type: str, primitive_type: str | None = None
) -> tuple[str, str | None, bool, bool]:
    """
    Parse a CloudFormation type into Python type info.

    Returns: (python_type, nested_type, is_list, is_map)
    """
    if primitive_type:
        type_map = {
            "String": "str",
            "Integer": "int",
            "Long": "int",
            "Double": "float",
            "Boolean": "bool",
            "Timestamp": "str",
            "Json": "dict[str, Any]",
        }
        return type_map.get(primitive_type, "Any"), None, False, False

    if cf_type == "List":
        return "list", None, True, False

    if cf_type == "Map":
        return "dict", None, False, True

    if cf_type == "Tag":
        return "Tag", "Tag", False, False

    # It's a nested type
    return cf_type, cf_type, False, False


def extract_service_name(resource_type: str) -> str:
    """Extract service name from resource type (e.g., 'AWS::S3::Bucket' -> 's3')."""
    parts = resource_type.split("::")
    if len(parts) >= 2:
        service = parts[1].lower()
        # Handle reserved keywords
        if service in PYTHON_KEYWORDS:
            service = PYTHON_KEYWORDS[service]
        return service
    return "unknown"


def extract_resource_name(resource_type: str) -> str:
    """Extract resource name from resource type.

    Example: 'AWS::S3::Bucket' -> 'Bucket'
    """
    parts = resource_type.split("::")
    if len(parts) >= 3:
        return parts[2]
    return resource_type


def parse_property(
    prop_name: str,
    prop_spec: dict,
    service: str,
    property_types: dict,
) -> PropertyDef:
    """Parse a single property definition."""
    python_name = to_snake_case(prop_name)

    # Determine the type
    primitive_type = prop_spec.get("PrimitiveType")
    cf_type = prop_spec.get("Type", "")
    item_type = prop_spec.get("ItemType") or prop_spec.get("PrimitiveItemType")

    python_type, nested_type, is_list, is_map = parse_cf_type(cf_type, primitive_type)

    # Handle list item types
    if is_list and item_type:
        if item_type in ("String", "Integer", "Long", "Double", "Boolean"):
            type_map = {
                "String": "str",
                "Integer": "int",
                "Long": "int",
                "Double": "float",
                "Boolean": "bool",
            }
            python_type = f"list[{type_map.get(item_type, 'Any')}]"
        else:
            python_type = f"list[{item_type}]"
            nested_type = item_type

    # Handle map value types
    if is_map and item_type:
        if item_type in ("String", "Integer", "Long", "Double", "Boolean"):
            type_map = {
                "String": "str",
                "Integer": "int",
                "Long": "int",
                "Double": "float",
                "Boolean": "bool",
            }
            python_type = f"dict[str, {type_map.get(item_type, 'Any')}]"
        else:
            python_type = f"dict[str, {item_type}]"
            nested_type = item_type

    return PropertyDef(
        name=python_name,
        original_name=prop_name,
        type=python_type,
        required=prop_spec.get("Required", False),
        documentation=prop_spec.get("Documentation", ""),
        nested_type=nested_type,
        is_list=is_list,
        is_map=is_map,
        item_type=item_type,
    )


def parse_resource(
    resource_type: str,
    resource_spec: dict,
    property_types: dict,
) -> ResourceDef:
    """Parse a single resource type."""
    service = extract_service_name(resource_type)
    name = extract_resource_name(resource_type)

    # Parse properties
    properties = []
    for prop_name, prop_spec in resource_spec.get("Properties", {}).items():
        prop = parse_property(prop_name, prop_spec, service, property_types)
        properties.append(prop)

    # Sort properties: required first, then alphabetical
    properties.sort(key=lambda p: (not p.required, p.name))

    # Parse attributes
    attributes = []
    for attr_name, attr_spec in resource_spec.get("Attributes", {}).items():
        primitive_type = attr_spec.get("PrimitiveType", "String")
        type_map = {
            "String": "str",
            "Integer": "int",
            "Long": "int",
            "Double": "float",
            "Boolean": "bool",
        }
        attributes.append(
            AttributeDef(
                name=attr_name,
                type=type_map.get(primitive_type, "str"),
            )
        )

    return ResourceDef(
        name=name,
        service=service,
        full_type=resource_type,
        documentation=resource_spec.get("Documentation", ""),
        properties=properties,
        attributes=attributes,
    )


def parse_property_type(
    prop_type_name: str,
    prop_type_spec: dict,
    property_types: dict,
) -> NestedTypeDef | None:
    """Parse a property type (nested structure)."""
    # Property types have format "AWS::Service::Resource.PropertyName"
    parts = prop_type_name.split(".")
    if len(parts) != 2:
        return None

    resource_part, type_name = parts
    service = extract_service_name(resource_part)

    # Skip if it's just a Tag (handled separately)
    if type_name == "Tag":
        return None

    # Parse properties
    properties = []
    for prop_name, prop_spec in prop_type_spec.get("Properties", {}).items():
        prop = parse_property(prop_name, prop_spec, service, property_types)
        properties.append(prop)

    # Sort properties
    properties.sort(key=lambda p: (not p.required, p.name))

    return NestedTypeDef(
        name=type_name,
        service=service,
        original_name=prop_type_name,
        properties=properties,
        documentation=prop_type_spec.get("Documentation", ""),
    )


def try_extract_enums_from_botocore(
    service: str, property_name: str
) -> list[str] | None:
    """Try to extract enum values from botocore service model."""
    try:
        from botocore import loaders

        loader = loaders.Loader()

        # Map CF service names to botocore service names
        service_map = {
            "lambda_": "lambda",
            "lambda": "lambda",
            "s3": "s3",
            "ec2": "ec2",
            "iam": "iam",
            "dynamodb": "dynamodb",
            "sqs": "sqs",
            "sns": "sns",
            "rds": "rds",
            "cloudwatch": "cloudwatch",
        }

        botocore_service = service_map.get(service, service)

        try:
            service_model = loader.load_service_model(botocore_service, "service-2")
        except Exception:
            return None

        # Search for enum in shapes
        shapes = service_model.get("shapes", {})
        for shape_name, shape_def in shapes.items():
            if shape_def.get("type") == "string" and "enum" in shape_def:
                # Check if the shape name matches the property
                if property_name.lower() in shape_name.lower():
                    return shape_def["enum"]

        return None
    except ImportError:
        return None
    except Exception:
        return None


def parse(validate: bool = False) -> IntermediateSchema:
    """
    Run the parse stage.

    Reads the CloudFormation spec and transforms it to intermediate format.
    """
    print("Stage 2: Parse")
    print("=" * 40)

    # Load manifest
    manifest_path = SPECS_DIR / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("manifest.json not found. Run fetch first.")

    manifest = json.loads(manifest_path.read_text())

    # Get version info
    cf_spec_version = ""
    botocore_version = ""
    for source in manifest.get("sources", []):
        if source["name"] == "cloudformation-spec":
            cf_spec_version = source.get("version", "")
        elif source["name"] == "botocore":
            botocore_version = source.get("version", "")

    # Load CloudFormation spec
    cf_spec_path = SPECS_DIR / "CloudFormationResourceSpecification.json"
    if not cf_spec_path.exists():
        raise FileNotFoundError("CloudFormation spec not found. Run fetch first.")

    print(f"Loading {cf_spec_path}...")
    cf_spec = json.loads(cf_spec_path.read_text())

    # Create intermediate schema
    schema = IntermediateSchema(
        schema_version="1.0",
        domain="aws",
        generated_at=datetime.now(UTC).isoformat(),
        cf_spec_version=cf_spec_version,
        botocore_version=botocore_version,
    )

    # Get property types for reference
    property_types = cf_spec.get("PropertyTypes", {})

    # Parse resource types
    resource_types = cf_spec.get("ResourceTypes", {})
    print(f"Parsing {len(resource_types)} resource types...")

    for resource_type, resource_spec in resource_types.items():
        try:
            resource = parse_resource(resource_type, resource_spec, property_types)
            schema.resources.append(resource)
        except Exception as e:
            print(f"  Warning: Failed to parse {resource_type}: {e}")

    # Parse property types (nested structures)
    print(f"Parsing {len(property_types)} property types...")

    for prop_type_name, prop_type_spec in property_types.items():
        try:
            nested = parse_property_type(prop_type_name, prop_type_spec, property_types)
            if nested:
                schema.nested_types.append(nested)
        except Exception as e:
            print(f"  Warning: Failed to parse {prop_type_name}: {e}")

    # Sort everything
    schema.resources.sort(key=lambda r: (r.service, r.name))
    schema.nested_types.sort(key=lambda n: (n.service, n.name))

    # Print summary
    services = set(r.service for r in schema.resources)
    print("\nParsed:")
    print(f"  {len(schema.resources)} resources")
    print(f"  {len(schema.nested_types)} nested types")
    print(f"  {len(services)} services")

    # Validation
    if validate:
        print("\nValidating...")
        errors = []

        for resource in schema.resources:
            if not resource.full_type:
                errors.append(f"Resource {resource.name} missing full_type")
            if not resource.service:
                errors.append(f"Resource {resource.name} missing service")

        if errors:
            for error in errors[:10]:
                print(f"  ERROR: {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")
            raise ValueError(f"Validation failed with {len(errors)} errors")

        print("  Validation passed!")

    # Write intermediate schema
    parsed_path = SPECS_DIR / "parsed.json"
    parsed_path.write_text(json.dumps(schema.to_dict(), indent=2))
    print(f"\nIntermediate schema written to {parsed_path}")

    return schema


def main():
    parser = argparse.ArgumentParser(
        description="Parse CloudFormation spec into intermediate format"
    )
    parser.add_argument("--validate", action="store_true", help="Run validation checks")
    args = parser.parse_args()

    try:
        parse(validate=args.validate)
        print("\nParse completed successfully!")
    except Exception as e:
        print(f"\nParse failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
