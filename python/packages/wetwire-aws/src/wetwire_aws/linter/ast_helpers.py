"""AST helper utilities for linting wetwire-aws code.

This module provides utility functions for analyzing Python ASTs.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def is_wetwire_aws(node: ast.ClassDef) -> bool:
    """Check if a class definition has the @wetwire_aws decorator.

    Args:
        node: A ClassDef AST node

    Returns:
        True if the class has @wetwire_aws decorator
    """
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "wetwire_aws":
            return True
        if isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Name) and func.id == "wetwire_aws":
                return True
    return False


def find_last_import_line(tree: ast.Module) -> int:
    """Find the line number of the last module-level import statement.

    Args:
        tree: The parsed AST

    Returns:
        Line number of the last import (1-indexed), or 0 if no imports
    """
    last_import_line = 0

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            # Get the end line of the import
            end_line = node.end_lineno or node.lineno
            last_import_line = max(last_import_line, end_line)

    return last_import_line


def extract_resource_annotation(node: ast.ClassDef) -> tuple[str, str] | None:
    """Extract the resource type annotation from a class.

    Looks for annotations like:
        resource: s3.Bucket
        resource: ec2.SecurityGroup

    Args:
        node: A ClassDef AST node

    Returns:
        Tuple of (module, type_name) or None if not found
    """
    for stmt in node.body:
        if isinstance(stmt, ast.AnnAssign):
            if isinstance(stmt.target, ast.Name) and stmt.target.id == "resource":
                annotation = stmt.annotation
                # Handle module.Type pattern
                if isinstance(annotation, ast.Attribute):
                    if isinstance(annotation.value, ast.Name):
                        module = annotation.value.id
                        type_name = annotation.attr
                        return (module, type_name)
    return None
