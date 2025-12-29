"""
Name conversion utilities for CloudFormation to Python.

Re-exports utilities from dataclass-dsl for backward compatibility.
"""

from __future__ import annotations

# Re-export from dataclass-dsl for backward compatibility
from dataclass_dsl import (
    PYTHON_KEYWORDS,
    is_valid_python_identifier,
    sanitize_class_name,
    sanitize_python_name,
    to_pascal_case,
    to_snake_case,
)

__all__ = [
    "PYTHON_KEYWORDS",
    "to_snake_case",
    "to_pascal_case",
    "sanitize_python_name",
    "sanitize_class_name",
    "is_valid_python_identifier",
]
