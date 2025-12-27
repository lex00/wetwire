"""
Code generation utilities.

Provides utilities for generating Python source code,
including formatting and type annotation helpers.
"""

import subprocess
import sys
from pathlib import Path

from wetwire.codegen.schema import PropertyDef

# Import black lazily to avoid requiring it at import time
_black = None


def _get_black():
    """Lazily import black."""
    global _black
    if _black is None:
        try:
            import black

            _black = black
        except ImportError as e:
            raise ImportError(
                "black is required for code formatting. "
                "Install with: pip install wetwire[codegen]"
            ) from e
    return _black


def python_type_for_property(prop: PropertyDef) -> str:
    """
    Get the Python type annotation for a property.

    Handles common types, lists, dicts, and nested types.

    Args:
        prop: The property definition

    Returns:
        A Python type annotation string
    """
    base_type = prop.type

    # Handle common cases
    if base_type in ("str", "int", "float", "bool"):
        return base_type

    if base_type.startswith("list[") or base_type.startswith("dict["):
        return base_type

    if base_type == "list":
        if prop.item_type:
            return f"list[{prop.item_type}]"
        return "list[Any]"

    if base_type == "dict":
        if prop.item_type:
            return f"dict[str, {prop.item_type}]"
        return "dict[str, Any]"

    # It's a nested type
    if prop.nested_type:
        return prop.nested_type

    return "Any"


def format_file(path: Path) -> bool:
    """
    Format a Python file using black.

    Args:
        path: Path to the Python file

    Returns:
        True if formatting succeeded, False otherwise
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "black", "--quiet", str(path)],
            capture_output=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def format_code(code: str) -> str:
    """
    Format Python code string using black.

    Args:
        code: The Python code to format

    Returns:
        The formatted code, or original if formatting fails
    """
    black = _get_black()
    try:
        return black.format_str(code, mode=black.Mode())
    except Exception:
        return code


def generate_dynamic_all() -> str:
    """
    Generate code for dynamic __all__ that exports all public classes.

    Returns:
        Python code string for dynamic __all__ generation
    """
    return '''
# Export all public classes dynamically
def _get_all():
    import sys
    return [
        name for name, obj in vars(sys.modules[__name__]).items()
        if isinstance(obj, type) and not name.startswith('_')
    ]

__all__ = _get_all()
'''


def generate_dataclass_field(
    name: str,
    python_type: str,
    optional: bool = True,
    use_factory: bool = False,
) -> str:
    """
    Generate a dataclass field declaration.

    Args:
        name: Field name
        python_type: Python type annotation
        optional: Whether the field is optional (adds | None)
        use_factory: Whether to use field(default_factory=...) for collections

    Returns:
        A dataclass field declaration line
    """
    if use_factory:
        if python_type.startswith("list"):
            return f"    {name}: {python_type} = field(default_factory=list)"
        elif python_type.startswith("dict"):
            return f"    {name}: {python_type} = field(default_factory=dict)"

    if optional:
        return f"    {name}: {python_type} | None = None"

    return f"    {name}: {python_type}"
