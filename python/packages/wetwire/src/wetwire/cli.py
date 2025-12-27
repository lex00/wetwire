"""
Base CLI framework for wetwire domain packages.

This module provides reusable CLI utilities that domain packages
(wetwire-aws, wetwire-k8s, etc.) can use to build their CLIs.

Utilities provided:
- discover_resources(): Import modules to trigger resource registration
- add_common_args(): Add standard CLI arguments (--module, --scope, --verbose)
- create_list_command(): Create a 'list' command handler
- create_validate_command(): Create a 'validate' command handler

Example usage in a domain package:
    from wetwire.cli import (
        discover_resources,
        add_common_args,
        create_list_command,
        create_validate_command,
    )
    from my_domain.registry import get_registry

    registry = get_registry()

    def get_resource_type(cls: type) -> str:
        # Domain-specific type extraction
        return getattr(cls, "_resource_type", "Unknown")

    list_command = create_list_command(registry, get_resource_type)
    validate_command = create_validate_command(registry)
"""

from __future__ import annotations

import argparse
import importlib
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wetwire.registry import ResourceRegistry


def discover_resources(
    module_path: str,
    registry: ResourceRegistry,
    verbose: bool = False,
) -> int:
    """
    Import a module to trigger resource registration.

    When a module is imported, any @wetwire decorated classes are
    automatically registered with the registry. This function imports
    the module and returns the count of newly registered resources.

    Args:
        module_path: Python module path to import (e.g., "myapp.infra")
        registry: The resource registry to count registrations
        verbose: If True, print discovery info to stderr

    Returns:
        Number of resources discovered (registered) from the import

    Raises:
        SystemExit: If the module cannot be imported
    """
    before = len(list(registry.get_all()))
    try:
        importlib.import_module(module_path)
    except ImportError as e:
        print(f"Error: Could not import module '{module_path}': {e}", file=sys.stderr)
        sys.exit(1)
    after = len(list(registry.get_all()))
    count = after - before
    if verbose:
        print(f"Discovered {count} resources from {module_path}", file=sys.stderr)
    return count


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """
    Add common CLI arguments used by most commands.

    Adds:
        --module/-m: Python module to import for resource discovery (repeatable)
        --scope/-s: Package scope to filter resources
        --verbose/-v: Enable verbose output

    Args:
        parser: ArgumentParser or subparser to add arguments to
    """
    parser.add_argument(
        "--module",
        "-m",
        dest="modules",
        action="append",
        help="Python module to import for resource discovery (can be repeated)",
    )
    parser.add_argument(
        "--scope",
        "-s",
        help="Package scope to filter resources",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )


def create_list_command(
    registry: ResourceRegistry,
    get_resource_type: Callable[[type], str],
) -> Callable[[argparse.Namespace], None]:
    """
    Create a 'list' command handler for a domain-specific CLI.

    The returned handler lists all registered resources with their
    resource types. It handles module discovery and scope filtering.

    Args:
        registry: The resource registry to list from
        get_resource_type: Function to extract the resource type string
            from a registered class. This is domain-specific.
            Example: lambda cls: cls._resource_type

    Returns:
        A command handler function that takes argparse.Namespace

    Example:
        def get_cf_type(cls):
            resource_cls = cls.__annotations__.get("resource")
            return getattr(resource_cls, "_resource_type", "Unknown")

        list_cmd = create_list_command(aws_registry, get_cf_type)
    """

    def list_command(args: argparse.Namespace) -> None:
        # Import modules to discover resources
        if args.modules:
            for module_path in args.modules:
                discover_resources(
                    module_path, registry, getattr(args, "verbose", False)
                )

        resources = list(registry.get_all(getattr(args, "scope", None)))
        if not resources:
            print("No resources registered.", file=sys.stderr)
            return

        print(f"Registered resources ({len(resources)}):\n")
        for resource_cls in sorted(resources, key=lambda r: r.__name__):
            resource_type = get_resource_type(resource_cls)
            print(f"  {resource_cls.__name__}: {resource_type}")

    return list_command


def create_validate_command(
    registry: ResourceRegistry,
) -> Callable[[argparse.Namespace], None]:
    """
    Create a 'validate' command handler for a domain-specific CLI.

    The returned handler validates that all resource references point
    to resources that exist in the registry. Uses graph-refs for
    dependency introspection.

    Args:
        registry: The resource registry to validate

    Returns:
        A command handler function that takes argparse.Namespace

    Raises:
        SystemExit: If validation fails (missing references)
    """

    def validate_command(args: argparse.Namespace) -> None:
        from graph_refs import get_dependencies

        # Import modules to discover resources
        if args.modules:
            for module_path in args.modules:
                discover_resources(
                    module_path, registry, getattr(args, "verbose", False)
                )

        resources = list(registry.get_all(getattr(args, "scope", None)))
        if not resources:
            print("Error: No resources registered.", file=sys.stderr)
            sys.exit(1)

        errors: list[str] = []
        warnings: list[str] = []
        resource_names = {r.__name__ for r in resources}

        for resource_cls in resources:
            try:
                deps = get_dependencies(resource_cls)
                for dep in deps:
                    if dep.__name__ not in resource_names:
                        errors.append(
                            f"{resource_cls.__name__} references {dep.__name__} "
                            "which is not registered"
                        )
            except Exception as e:
                warnings.append(
                    f"{resource_cls.__name__}: Could not compute dependencies: {e}"
                )

        # Report results
        verbose = getattr(args, "verbose", False)
        if errors:
            print("Validation FAILED:", file=sys.stderr)
            for error in errors:
                print(f"  ERROR: {error}", file=sys.stderr)
            if warnings and verbose:
                for warning in warnings:
                    print(f"  WARNING: {warning}", file=sys.stderr)
            sys.exit(1)
        elif warnings and verbose:
            print("Validation passed with warnings:", file=sys.stderr)
            for warning in warnings:
                print(f"  WARNING: {warning}", file=sys.stderr)
        else:
            print(f"Validation passed: {len(resources)} resources OK")

    return validate_command
