"""
The @wetwire decorator for declarative dataclass resources.

This module provides the decorator that enables the wetwire pattern:

    @wetwire
    class MyBucket:
        resource: Bucket
        bucket_name = "my-bucket"

    bucket = MyBucket()  # No parameters needed!

The decorator also enables the no-parens attribute access pattern:

    @wetwire
    class MyFunction:
        resource: Function
        role = MyRole.Arn    # Returns AttrRef(MyRole, "Arn")
        vpc = MyVPC          # Class reference (already works)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import MISSING
from dataclasses import dataclass as make_dataclass
from dataclasses import field as dc_field
from typing import Any, TypeVar, dataclass_transform, get_type_hints

from wetwire._internal.wrapper_utils import get_wrapped_type, is_wrapper_class
from wetwire.refs import AttrRef, WetWireMeta
from wetwire.registry import registry

T = TypeVar("T")


def _apply_metaclass(cls: type[T], metaclass: type) -> type[T]:
    """
    Apply a metaclass to an existing class.

    This creates a new class with the same name, bases, and attributes,
    but with the specified metaclass. Useful for adding metaclass behavior
    to a class after @dataclass has been applied.
    """
    # Get the class dict, excluding __dict__ and __weakref__
    class_dict = {}
    for key, value in cls.__dict__.items():
        if key in ("__dict__", "__weakref__"):
            continue
        class_dict[key] = value

    # Create new class with the metaclass
    new_cls = metaclass(cls.__name__, cls.__bases__, class_dict)

    # Preserve module and qualname
    new_cls.__module__ = cls.__module__
    new_cls.__qualname__ = cls.__qualname__

    return new_cls  # type: ignore[return-value]


@dataclass_transform()
def wetwire(
    maybe_cls: type[T] | None = None,
    *,
    register: bool = True,
) -> type[T] | Callable[[type[T]], type[T]]:
    """
    Decorator that enables the wetwire declarative pattern.

    This decorator automatically applies @dataclass and sets up the
    wrapper class pattern. Resources are automatically registered
    with the global registry for template building.

    Usage:
        >>> from wetwire import wetwire
        >>>
        >>> @wetwire
        ... class MyBucket:
        ...     resource: Bucket
        ...     bucket_name: str = "my-bucket"
        ...
        >>> bucket = MyBucket()  # Works! No 'resource' parameter needed

    Args:
        maybe_cls: The class to wrap (used when decorator is called without parens)
        register: If True (default), auto-register with global registry

    Returns:
        The decorator function or the modified class
    """

    def decorator(cls: type[T]) -> type[T]:
        """Apply wetwire modifications to the class."""
        # Detect and handle all defaults (both mutable and immutable)
        # Mutable defaults (lists, dicts) -> field(default_factory=...)
        # Immutable defaults -> add annotation so they become dataclass fields
        for attr_name in list(vars(cls).keys()):
            if attr_name.startswith("_"):
                continue

            attr_value = getattr(cls, attr_name, MISSING)
            if attr_value is MISSING:
                continue

            # Skip class methods, staticmethods, properties, etc.
            if callable(attr_value) and not isinstance(attr_value, type):
                continue
            if isinstance(attr_value, (classmethod, staticmethod, property)):
                continue

            # Add type annotation if missing
            if not hasattr(cls, "__annotations__"):
                cls.__annotations__ = {}
            if attr_name not in cls.__annotations__:
                # Infer type from value
                if isinstance(attr_value, list):
                    cls.__annotations__[attr_name] = list[Any]
                elif isinstance(attr_value, dict):
                    cls.__annotations__[attr_name] = dict[str, Any]
                elif isinstance(attr_value, type):
                    # This is a class reference (the no-parens pattern)
                    # We'll handle this specially but still need an annotation
                    cls.__annotations__[attr_name] = type[Any]
                elif isinstance(attr_value, AttrRef):
                    # This is an attribute reference (MyRole.Arn pattern)
                    cls.__annotations__[attr_name] = AttrRef
                else:
                    cls.__annotations__[attr_name] = type(attr_value)

            # Check if this is a mutable default (list, dict, or class instance)
            if isinstance(attr_value, list):
                # Convert to field(default_factory=...) with a copy
                default_list = list(attr_value)
                setattr(
                    cls,
                    attr_name,
                    dc_field(default_factory=lambda v=default_list: list(v)),
                )
            elif isinstance(attr_value, dict):
                # Convert to field(default_factory=...) with a copy
                default_dict = dict(attr_value)
                setattr(
                    cls,
                    attr_name,
                    dc_field(default_factory=lambda v=default_dict: dict(v)),
                )
            elif isinstance(attr_value, AttrRef):
                # AttrRef is immutable, use directly as default
                pass
            elif hasattr(attr_value, "__class__") and not isinstance(
                attr_value, (str, int, float, bool, type(None), type)
            ):
                # Complex object - use copy if possible
                import copy

                try:
                    default_copy = copy.copy(attr_value)
                    setattr(
                        cls,
                        attr_name,
                        dc_field(default_factory=lambda v=default_copy: copy.copy(v)),
                    )
                except Exception:
                    # If copy fails, fall back to returning the same instance
                    setattr(
                        cls, attr_name, dc_field(default_factory=lambda v=attr_value: v)
                    )

        # Add a default to the 'resource' field
        if hasattr(cls, "__annotations__"):
            if "resource" in cls.__annotations__:
                if not hasattr(cls, "resource") or getattr(cls, "resource") is MISSING:
                    setattr(cls, "resource", None)

        # Handle fields whose type is a wrapper class
        # Give these fields None defaults
        if hasattr(cls, "__annotations__"):
            try:
                type_hints = get_type_hints(cls)
                for field_name, field_type in type_hints.items():
                    if field_name == "resource":
                        continue
                    # Check if the type is a wrapper class
                    if isinstance(field_type, type) and is_wrapper_class(field_type):
                        if not hasattr(cls, field_name):
                            setattr(cls, field_name, None)
            except Exception:
                # If we can't resolve type hints (forward references),
                # skip this optimization
                pass

        # Store original __post_init__ if it exists
        original_post_init = getattr(cls, "__post_init__", None)

        def _wetwire_post_init(self: Any) -> None:
            """Auto-initialize wrapper during instantiation."""
            # Call original __post_init__ if it existed
            if original_post_init is not None:
                original_post_init(self)

        # Add the __post_init__ method
        cls.__post_init__ = _wetwire_post_init  # type: ignore[attr-defined]

        # Apply @dataclass decorator
        cls = make_dataclass(cls)  # type: ignore[assignment]

        # Apply WetWireMeta metaclass to enable no-parens attribute access
        # (e.g., MyRole.Arn returns AttrRef(MyRole, "Arn"))
        cls = _apply_metaclass(cls, WetWireMeta)

        # Mark as a wetwire class
        cls._wetwire_marker = True  # type: ignore[attr-defined]

        # Auto-register if requested
        if register:
            wrapped_type = get_wrapped_type(cls)
            registry.register(cls, wrapped_type)

        return cls

    # Support both @wetwire and @wetwire() syntax
    if maybe_cls is None:
        return decorator
    return decorator(maybe_cls)
