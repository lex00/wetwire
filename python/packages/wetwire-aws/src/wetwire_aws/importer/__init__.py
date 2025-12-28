"""CloudFormation template importer.

This module provides functionality to convert existing CloudFormation
templates (YAML/JSON) into Python code using wetwire-aws.

Public API:
- parse_template(): Parse a CloudFormation template into IR
- generate_code(): Generate a single Python file from IR
- generate_package(): Generate a multi-file Python package from IR
- import_template(): High-level function combining parsing and code generation

Example:
    >>> from wetwire_aws.importer import import_template
    >>> files = import_template("template.yaml", "my_stack")
    >>> for filename, content in files.items():
    ...     print(f"Generated: {filename}")
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from .codegen import generate_code, generate_package
from .ir import (
    IRCondition,
    IRIntrinsic,
    IRMapping,
    IROutput,
    IRParameter,
    IRProperty,
    IRResource,
    IRTemplate,
    IntrinsicType,
)
from .parser import parse_template

__all__ = [
    # High-level API
    "import_template",
    # Parser
    "parse_template",
    # Code generation
    "generate_code",
    "generate_package",
    # IR types
    "IRTemplate",
    "IRResource",
    "IRParameter",
    "IROutput",
    "IRMapping",
    "IRCondition",
    "IRProperty",
    "IRIntrinsic",
    "IntrinsicType",
]


def import_template(
    source: Union[str, Path],
    package_name: str | None = None,
    *,
    single_file: bool = False,
) -> dict[str, str]:
    """Import a CloudFormation template and generate Python code.

    This is the high-level entry point for converting CloudFormation
    templates to wetwire-aws Python code.

    Args:
        source: Path to a CloudFormation template file (YAML or JSON).
        package_name: Name for the generated package. If not provided,
            derived from the source filename.
        single_file: If True, generate a single Python file instead of
            a package with multiple files.

    Returns:
        Dict mapping relative file paths to file contents.

    Example:
        >>> files = import_template("template.yaml", "my_stack")
        >>> for path, content in files.items():
        ...     Path(path).parent.mkdir(parents=True, exist_ok=True)
        ...     Path(path).write_text(content)
    """
    # Resolve source path
    source_path = Path(source)

    # Derive package name from filename if not provided
    if package_name is None:
        package_name = source_path.stem.replace("-", "_").replace(".", "_")

    # Parse the template
    ir = parse_template(source_path)

    # Generate code
    if single_file:
        code = generate_code(ir)
        return {f"{package_name}.py": code}
    else:
        return generate_package(ir, package_name)
