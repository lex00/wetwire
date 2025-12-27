"""
Computed field support for derived values.

Enables fields whose values are computed at serialization time.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class ComputedDescriptor:
    """
    Descriptor that defers computation until access.

    The wrapped function is called each time the attribute is accessed,
    allowing for dynamic computation based on current instance state.
    """

    def __init__(self, func: Callable[..., Any]) -> None:
        self.func = func
        self.name: str = ""

    def __set_name__(self, owner: type[Any], name: str) -> None:
        self.name = name

    def __get__(self, obj: Any, objtype: type[Any] | None = None) -> Any:
        if obj is None:
            return self
        return self.func(obj)

    def __repr__(self) -> str:
        return f"<computed {self.name}>"


def computed(func: Callable[..., T]) -> T:
    """
    Mark a method as a computed field.

    The method is called at access time (including serialization),
    allowing values to be derived from other fields.

    Example:
        >>> @wetwire
        ... class MyBucket:
        ...     resource: Bucket
        ...     project: str = "myapp"
        ...     environment: str = "prod"
        ...
        ...     @computed
        ...     def bucket_name(self) -> str:
        ...         return f"{self.project}-{self.environment}-data"
        ...
        >>> bucket = MyBucket()
        >>> bucket.bucket_name
        'myapp-prod-data'

    Args:
        func: The method to compute the value

    Returns:
        A descriptor that computes the value on access
    """
    return ComputedDescriptor(func)  # type: ignore[return-value]
