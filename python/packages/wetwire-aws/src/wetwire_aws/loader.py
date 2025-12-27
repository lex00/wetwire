"""
AWS CloudFormation resource loader.

Convenience wrapper around wetwire.loader.setup_resources with
AWS-specific stub configuration.

Usage in a resources package __init__.py:
    from wetwire_aws.loader import setup_resources
    setup_resources(__file__, __name__, globals())
"""

from __future__ import annotations

from typing import Any

from wetwire.loader import setup_resources as _setup_resources

from wetwire_aws.stubs import AWS_STUB_CONFIG


def setup_resources(
    init_file: str,
    package_name: str,
    package_globals: dict[str, Any],
    *,
    generate_stubs: bool = True,
) -> None:
    """Set up AWS CloudFormation resource imports.

    Wrapper around wetwire.loader.setup_resources with AWS-specific
    stub configuration pre-applied.

    This function:
    1. Finds all .py files in the package directory
    2. Parses them to find class definitions and Ref/Attr annotations
    3. Builds a dependency graph from the annotations
    4. Imports modules in topological order
    5. Injects previously-loaded classes into each module's namespace
    6. Generates .pyi stubs with AWS-specific imports for IDE support

    Args:
        init_file: Path to __init__.py (__file__)
        package_name: Package name (__name__)
        package_globals: Package globals dict (globals())
        generate_stubs: Whether to generate .pyi files (default: True)

    Example:
        # In myapp/resources/__init__.py
        from wetwire_aws.loader import setup_resources
        setup_resources(__file__, __name__, globals())
    """
    _setup_resources(
        init_file,
        package_name,
        package_globals,
        stub_config=AWS_STUB_CONFIG,
        generate_stubs=generate_stubs,
    )
