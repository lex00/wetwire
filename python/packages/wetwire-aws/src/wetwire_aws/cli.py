"""
CLI for wetwire-aws template generation.

Usage:
    wetwire-aws build [OPTIONS]
    wetwire-aws validate [OPTIONS]
    wetwire-aws list [OPTIONS]
    wetwire-aws import TEMPLATE [-o OUTPUT]
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

    # Import a CloudFormation template to Python
    wetwire-aws import template.yaml -o my_stack/
"""

import argparse
import sys
from pathlib import Path

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


def lint_command(args: argparse.Namespace) -> None:
    """Lint Python code for wetwire-aws issues."""
    from wetwire_aws.linter import fix_file, lint_file

    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path not found: {path}", file=sys.stderr)
        sys.exit(1)

    # Collect Python files
    if path.is_file():
        files = [path]
    else:
        files = list(path.rglob("*.py"))

    if not files:
        print(f"No Python files found in {path}", file=sys.stderr)
        sys.exit(0)

    total_issues = 0
    files_with_issues = 0

    for filepath in files:
        try:
            if args.fix:
                # Read original to check if we made changes
                original = filepath.read_text()
                fixed = fix_file(str(filepath), write=True)
                if fixed != original:
                    print(f"Fixed: {filepath}")
                    files_with_issues += 1
            else:
                issues = lint_file(str(filepath))
                if issues:
                    files_with_issues += 1
                    for issue in issues:
                        print(f"{filepath}:{issue.line}:{issue.column}: {issue.rule_id} {issue.message}")
                        total_issues += 1
        except Exception as e:
            if args.verbose:
                print(f"Error processing {filepath}: {e}", file=sys.stderr)

    if not args.fix:
        if total_issues:
            print(f"\nFound {total_issues} issues in {files_with_issues} files", file=sys.stderr)
            sys.exit(1)
        else:
            if args.verbose:
                print(f"No issues found in {len(files)} files", file=sys.stderr)
            sys.exit(0)


def import_command(args: argparse.Namespace) -> None:
    """Import a CloudFormation template and generate Python code."""
    from wetwire_aws.importer import import_template

    source = Path(args.template)
    if not source.exists():
        print(f"Error: Template file not found: {source}", file=sys.stderr)
        sys.exit(1)

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = Path.cwd()

    # Determine package name
    if args.name:
        package_name = args.name
    else:
        package_name = source.stem.replace("-", "_").replace(".", "_")

    # Generate code
    try:
        files = import_template(
            source,
            package_name=package_name,
            single_file=args.single_file,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Write files
    for filepath, content in files.items():
        full_path = output_dir / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)

        if full_path.exists() and not args.force:
            print(f"Skipping (exists): {full_path}", file=sys.stderr)
            continue

        full_path.write_text(content)
        if args.verbose:
            print(f"Created: {full_path}", file=sys.stderr)

    print(f"Imported {len(files)} files to {output_dir / package_name}", file=sys.stderr)


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

    # Import command
    import_parser = subparsers.add_parser(
        "import",
        help="Import CloudFormation template to Python code",
    )
    import_parser.add_argument(
        "template",
        help="Path to CloudFormation template (YAML or JSON)",
    )
    import_parser.add_argument(
        "--output",
        "-o",
        help="Output directory (default: current directory)",
    )
    import_parser.add_argument(
        "--name",
        "-n",
        help="Package name (default: derived from template filename)",
    )
    import_parser.add_argument(
        "--single-file",
        action="store_true",
        help="Generate a single Python file instead of a package",
    )
    import_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Overwrite existing files",
    )
    import_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    import_parser.set_defaults(func=import_command)

    # Lint command
    lint_parser = subparsers.add_parser(
        "lint",
        help="Lint wetwire-aws code for issues",
    )
    lint_parser.add_argument(
        "path",
        help="Path to Python file or directory to lint",
    )
    lint_parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix detected issues",
    )
    lint_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    lint_parser.set_defaults(func=lint_command)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
