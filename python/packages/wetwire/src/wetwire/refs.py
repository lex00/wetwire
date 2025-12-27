"""
Runtime reference markers for the no-parens pattern.

This module provides runtime marker classes that enable the wetwire pattern:

    @wetwire
    class MyFunction:
        resource: Function
        role = MyRole.Arn    # Returns AttrRef(MyRole, "Arn")
        vpc = MyVPC          # The class itself (already works)

These markers are detected by the serializer and converted to the
appropriate format (e.g., {"Fn::GetAtt": [...]} for CloudFormation).

Note: The typing primitives (Ref[T], Attr[T, name]) are in graph-refs.
      This module provides the runtime counterparts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class AttrRef:
    """
    Runtime marker for attribute references.

    Created when accessing an attribute on a wetwire-decorated class:

        role = MyRole.Arn  # Returns AttrRef(MyRole, "Arn")

    The serializer detects this and converts to the appropriate format.
    """

    __slots__ = ("target", "attr")

    def __init__(self, target: type, attr: str) -> None:
        """
        Create an attribute reference marker.

        Args:
            target: The class being referenced (e.g., MyRole)
            attr: The attribute name (e.g., "Arn")
        """
        self.target = target
        self.attr = attr

    def __repr__(self) -> str:
        target_name = getattr(self.target, "__name__", str(self.target))
        return f"AttrRef({target_name}, {self.attr!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AttrRef):
            return NotImplemented
        return self.target is other.target and self.attr == other.attr

    def __hash__(self) -> int:
        return hash((id(self.target), self.attr))


class WetWireMeta(type):
    """
    Metaclass that enables the no-parens attribute access pattern.

    When a class uses this metaclass, accessing undefined class attributes
    returns an AttrRef marker:

        @wetwire
        class MyRole:
            resource: Role
            ...

        MyRole.Arn  # Returns AttrRef(MyRole, "Arn")
    """

    # Attributes that should NOT return AttrRef (Python internals, etc.)
    _RESERVED_ATTRS = frozenset({
        # Python internals
        "__name__",
        "__qualname__",
        "__module__",
        "__dict__",
        "__doc__",
        "__annotations__",
        "__bases__",
        "__mro__",
        "__class__",
        "__weakref__",
        "__subclasshook__",
        "__init_subclass__",
        # Dataclass internals
        "__dataclass_fields__",
        "__dataclass_params__",
        "__post_init__",
        # Common dunder methods
        "__init__",
        "__new__",
        "__repr__",
        "__str__",
        "__eq__",
        "__hash__",
        "__reduce__",
        "__reduce_ex__",
        "__getstate__",
        "__setstate__",
        # Type checking
        "__origin__",
        "__args__",
        "__parameters__",
        # Wetwire internals
        "_wetwire_marker",
        "_resource_type",
    })

    def __getattr__(cls, name: str) -> Any:
        """
        Return AttrRef for undefined attribute access.

        This enables patterns like:
            role = MyRole.Arn  # AttrRef(MyRole, "Arn")
        """
        # Don't intercept reserved attributes
        if name.startswith("_") or name in cls._RESERVED_ATTRS:
            raise AttributeError(
                f"type object {cls.__name__!r} has no attribute {name!r}"
            )

        # Return an AttrRef marker
        return AttrRef(cls, name)


def is_attr_ref(obj: Any) -> bool:
    """Check if an object is an AttrRef marker."""
    return isinstance(obj, AttrRef)


def is_class_ref(obj: Any) -> bool:
    """Check if an object is a class reference (the no-parens pattern)."""
    return isinstance(obj, type) and hasattr(obj, "_wetwire_marker")
