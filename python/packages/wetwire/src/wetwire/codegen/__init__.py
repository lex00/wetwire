"""
Code generation utilities for wetwire.

This module provides shared utilities for generating Python code
from infrastructure provider specifications. It is used by domain
packages like wetwire-aws and can be reused for other providers.

Install with: pip install wetwire[codegen]
"""

from wetwire.codegen.schema import (
    AttributeDef,
    EnumDef,
    IntermediateSchema,
    NestedTypeDef,
    PropertyDef,
    ResourceDef,
)
from wetwire.codegen.transforms import (
    PYTHON_KEYWORDS,
    escape_python_keyword,
    to_class_name,
    to_python_identifier,
    to_snake_case,
)

# Fetcher and generator utilities require optional dependencies
# Import them conditionally or let them raise ImportError when used

__all__ = [
    # Schema types
    "PropertyDef",
    "AttributeDef",
    "ResourceDef",
    "EnumDef",
    "NestedTypeDef",
    "IntermediateSchema",
    # Transform utilities
    "PYTHON_KEYWORDS",
    "escape_python_keyword",
    "to_snake_case",
    "to_class_name",
    "to_python_identifier",
]
