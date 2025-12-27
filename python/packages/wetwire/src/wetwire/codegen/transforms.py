"""
Name and type transformation utilities for code generation.

These functions handle converting provider-specific naming conventions
to Python-compatible names, including keyword escaping.
"""

import re

# Reserved Python keywords and builtins that need renaming
PYTHON_KEYWORDS: dict[str, str] = {
    # Python keywords
    "and": "and_",
    "as": "as_",
    "assert": "assert_",
    "async": "async_",
    "await": "await_",
    "break": "break_",
    "class": "class_",
    "continue": "continue_",
    "def": "def_",
    "del": "del_",
    "elif": "elif_",
    "else": "else_",
    "except": "except_",
    "finally": "finally_",
    "for": "for_",
    "from": "from_",
    "global": "global_",
    "if": "if_",
    "import": "import_",
    "in": "in_",
    "is": "is_",
    "lambda": "lambda_",
    "None": "none_",
    "nonlocal": "nonlocal_",
    "not": "not_",
    "or": "or_",
    "pass": "pass_",
    "raise": "raise_",
    "return": "return_",
    "True": "true_",
    "False": "false_",
    "try": "try_",
    "type": "type_",
    "while": "while_",
    "with": "with_",
    "yield": "yield_",
    # Names that shadow common imports
    "field": "field_",
    "dataclass": "dataclass_",
}


def escape_python_keyword(name: str) -> str:
    """
    Escape a name if it's a Python keyword or reserved identifier.

    Args:
        name: The name to potentially escape

    Returns:
        The escaped name if it's a keyword, otherwise the original name
    """
    return PYTHON_KEYWORDS.get(name, name)


def to_snake_case(name: str) -> str:
    """
    Convert PascalCase or camelCase to snake_case.

    Handles acronyms correctly (e.g., VPCId -> vpc_id, not v_p_c_id).
    Also escapes Python keywords.

    Args:
        name: The name to convert

    Returns:
        The snake_case version of the name, with keywords escaped
    """
    # Handle acronyms (e.g., VPCId -> vpc_id, not v_p_c_id)
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    result = s2.lower()

    # Handle Python keywords
    return escape_python_keyword(result)


def to_class_name(name: str) -> str:
    """
    Convert a name to a valid Python class name.

    Removes any non-alphanumeric characters.

    Args:
        name: The name to convert

    Returns:
        A valid Python class name
    """
    # Remove any non-alphanumeric characters
    return re.sub(r"[^a-zA-Z0-9]", "", name)


def to_python_identifier(value: str) -> str:
    """
    Convert any string value to a valid Python identifier.

    Used for converting enum values to valid Python names.

    Args:
        value: The value to convert (e.g., "us-east-1", "3.12")

    Returns:
        A valid Python identifier (e.g., "US_EAST_1", "V3_12")
    """
    # Replace common separators with underscores
    result = value.replace("-", "_").replace(".", "_").replace("/", "_")
    result = result.replace(" ", "_").replace(":", "_")

    # Remove any remaining invalid characters
    result = re.sub(r"[^a-zA-Z0-9_]", "", result)

    # If starts with a digit, prefix with underscore or letter
    if result and result[0].isdigit():
        result = "V" + result

    # If empty after cleaning, use a placeholder
    if not result:
        result = "UNKNOWN"

    return result.upper()
