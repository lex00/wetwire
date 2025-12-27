"""
CLI for wetwire-aws template generation.

Usage:
    wetwire-aws build [OPTIONS]
    wetwire-aws validate [OPTIONS]
    wetwire-aws list [OPTIONS]
    wetwire-aws --help

Examples:
    # Generate CloudFormation JSON to stdout
    wetwire-aws build --module myapp.infra > template.json

    # Generate with specific package scope
    wetwire-aws build --module myapp --scope myapp.infra

    # Generate YAML format
    wetwire-aws build --module myapp.infra --format yaml

    # Validate references without generating
    wetwire-aws validate --module myapp.infra

    # List registered resources
    wetwire-aws list --module myapp.infra
"""

import argparse
import sys

from wetwire_aws.cli_utils import (
    add_common_args,
    create_list_command,
    create_validate_command,
    discover_resources,
)

from wetwire_aws.decorator import get_aws_registry
from wetwire_aws.template import CloudFormationTemplate


def get_cf_resource_type(cls: type) -> str:
    """
    Extract CloudFormation resource type from a wrapper class.

    Args:
        cls: The wrapper class decorated with @wetwire_aws

    Returns:
        The CloudFormation resource type string (e.g., "AWS::S3::Bucket")
    """
    annotations = getattr(cls, "__annotations__", {})
    resource_type_cls = annotations.get("resource")
    if resource_type_cls and hasattr(resource_type_cls, "_resource_type"):
        resource_type: str = resource_type_cls._resource_type
        return resource_type
    return "Unknown"


def build_command(args: argparse.Namespace) -> None:
    """Generate CloudFormation template from registered resources."""
    registry = get_aws_registry()

    # Import modules to discover resources
    if args.modules:
        for module_path in args.modules:
            discover_resources(module_path, registry, args.verbose)

    # Check if any resources are registered
    resources = list(registry.get_all(args.scope))
    if not resources:
        if args.scope:
            print(f"Error: No resources found in scope '{args.scope}'", file=sys.stderr)
        else:
            print("Error: No resources registered.", file=sys.stderr)
            print(
                "Hint: Import your resource modules with --module, e.g.:",
                file=sys.stderr,
            )
            print("  wetwire-aws build --module myapp.infra", file=sys.stderr)
        sys.exit(1)

    # Generate template
    template = CloudFormationTemplate.from_registry(
        scope_package=args.scope,
        description=args.description or "",
    )

    # Output in requested format
    if args.format == "yaml":
        try:
            output = template.to_yaml()
        except ImportError:
            print(
                "Error: PyYAML required for YAML output. "
                "Install with: pip install pyyaml",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        output = template.to_json(indent=args.indent)

    print(output)

    if args.verbose:
        print(
            f"\nGenerated template with {len(template.resources)} resources",
            file=sys.stderr,
        )


def main() -> None:
    """Main CLI entry point."""
    registry = get_aws_registry()

    parser = argparse.ArgumentParser(
        prog="wetwire-aws",
        description="Generate CloudFormation templates from wetwire-aws resources",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Build command (AWS-specific)
    build_parser = subparsers.add_parser(
        "build",
        help="Generate CloudFormation template",
    )
    add_common_args(build_parser)
    build_parser.add_argument(
        "--format",
        "-f",
        choices=["json", "yaml"],
        default="json",
        help="Output format (default: json)",
    )
    build_parser.add_argument(
        "--indent",
        "-i",
        type=int,
        default=2,
        help="JSON indentation (default: 2)",
    )
    build_parser.add_argument(
        "--description",
        "-d",
        help="Template description",
    )
    build_parser.set_defaults(func=build_command)

    # Validate command (uses base implementation)
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate resources and references",
    )
    add_common_args(validate_parser)
    validate_parser.set_defaults(func=create_validate_command(registry))

    # List command (uses base implementation)
    list_parser = subparsers.add_parser(
        "list",
        help="List registered resources",
    )
    add_common_args(list_parser)
    list_parser.set_defaults(func=create_list_command(registry, get_cf_resource_type))

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
