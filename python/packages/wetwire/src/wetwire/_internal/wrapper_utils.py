"""Utilities for working with wrapper dataclasses."""

from __future__ import annotations

import sys
from dataclasses import is_dataclass
from typing import Any, get_type_hints


def is_wrapper_class(cls: type[Any]) -> bool:
    """
    Check if a class is a wrapper class (has a 'resource' field).

    A wrapper class wraps an underlying resource type via a 'resource:' field
    annotation.

    Args:
        cls: The class to check

    Returns:
        True if the class has a 'resource' field annotation

    Examples:
        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class MyBucket:
        ...     resource: SomeBucketType
        ...     bucket_name: str = "my-bucket"
        ...
        >>> is_wrapper_class(MyBucket)
        True
    """
    if not is_dataclass(cls):
        return False

    try:
        type_hints = get_type_hints(cls)
        return "resource" in type_hints
    except Exception:
        # If get_type_hints fails (e.g., forward references can't be resolved),
        # fall back to checking raw annotations
        annotations = getattr(cls, "__annotations__", {})
        return "resource" in annotations


def get_wrapped_type(cls: type[Any]) -> type[Any] | None:
    """
    Get the wrapped type from a wrapper class.

    Args:
        cls: A wrapper class

    Returns:
        The wrapped class (from the 'resource' field), or None if not a wrapper

    Examples:
        >>> from dataclasses import dataclass
        >>> class BucketType: pass
        >>> @dataclass
        ... class MyBucket:
        ...     resource: BucketType
        ...
        >>> get_wrapped_type(MyBucket)
        <class 'BucketType'>
    """
    if not is_wrapper_class(cls):
        return None

    try:
        # Get the raw annotation (might be a string with PEP 563)
        annotations = getattr(cls, "__annotations__", {})

        if "resource" not in annotations:
            return None

        annotation = annotations["resource"]

        # If it's already a type, return it directly
        if isinstance(annotation, type):
            return annotation

        # If it's a string (PEP 563), resolve it
        if isinstance(annotation, str):
            module = sys.modules.get(cls.__module__)
            if module:
                globalns = vars(module)

                # Handle dotted names like "module.ClassName"
                if "." in annotation:
                    try:
                        resolved = eval(annotation, globalns)  # noqa: S307
                        if isinstance(resolved, type):
                            return resolved
                    except Exception:
                        pass

                # Check if it's a simple name in globals
                if annotation in globalns:
                    resolved = globalns[annotation]
                    if isinstance(resolved, type):
                        return resolved

                # Fall back to get_type_hints
                try:
                    type_hints = get_type_hints(cls, globalns=globalns)
                    return type_hints.get("resource")
                except Exception:
                    pass

        return None
    except Exception:
        return None


def get_logical_id(wrapper_cls: type[Any]) -> str:
    """
    Get the logical ID for a wrapper class.

    By default, uses the class name. Override by setting _logical_id class attribute.

    Args:
        wrapper_cls: The wrapper class

    Returns:
        The logical ID string
    """
    return getattr(wrapper_cls, "_logical_id", wrapper_cls.__name__)
