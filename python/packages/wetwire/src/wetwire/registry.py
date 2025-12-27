"""
Global registry for @wetwire wrapper classes.

This module provides auto-registration for wrapper resources,
enabling multi-file template organization and type-based queries.

Example:
    # resources/network.py
    @wetwire
    class MyVPC:
        resource: VPC
        cidr_block = "10.0.0.0/16"
        # Automatically registered!

    # main.py
    from wetwire import registry

    # Get all registered resources
    all_resources = registry.get_all()

    # Query by type
    vpcs = registry.get_by_type(VPC)
"""

from __future__ import annotations

from threading import Lock
from typing import Any


class ResourceRegistry:
    """
    Global registry for @wetwire wrapper classes.

    Resources auto-register when decorated, enabling:
    - Multi-file template organization
    - Type-based queries
    - Automatic template building via Template.from_registry()
    """

    def __init__(self) -> None:
        self._resources: dict[str, type[Any]] = {}  # class_name -> class
        self._by_type: dict[type[Any] | str, list[type[Any]]] = (
            {}
        )  # resource_type -> [classes]
        self._lock = Lock()

    def register(
        self,
        wrapper_cls: type[Any],
        resource_type: type[Any] | str | None = None,
    ) -> None:
        """
        Register a wrapper class.

        Args:
            wrapper_cls: The @wetwire decorated class
            resource_type: The underlying resource type (optional). If not provided,
                          extracted from the 'resource' field annotation.
        """
        with self._lock:
            name = wrapper_cls.__name__
            self._resources[name] = wrapper_cls

            # Determine resource type
            if resource_type is None:
                from wetwire._internal.wrapper_utils import get_wrapped_type

                resource_type = get_wrapped_type(wrapper_cls)

            if resource_type is not None:
                if resource_type not in self._by_type:
                    self._by_type[resource_type] = []
                self._by_type[resource_type].append(wrapper_cls)

    def get_all(self, scope_package: str | None = None) -> list[type[Any]]:
        """
        Get all registered wrapper classes, optionally filtered by package.

        Args:
            scope_package: If provided, only return resources from modules
                that start with this package name.

        Returns:
            List of registered wrapper classes.

        Example:
            >>> registry.get_all()  # All resources
            >>> registry.get_all("myproject.aws")  # Only from myproject.aws.*
        """
        with self._lock:
            resources = list(self._resources.values())

        if scope_package:
            resources = [r for r in resources if r.__module__.startswith(scope_package)]
        return resources

    def get_by_type(self, resource_type: type[Any] | str) -> list[type[Any]]:
        """
        Get wrapper classes by their underlying resource type.

        Args:
            resource_type: The resource type class or string identifier

        Returns:
            List of wrapper classes that wrap the specified resource type

        Example:
            >>> from wetwire_aws.resources import VPC
            >>> vpcs = registry.get_by_type(VPC)
        """
        with self._lock:
            return list(self._by_type.get(resource_type, []))

    def get_by_name(self, name: str) -> type[Any] | None:
        """
        Get a wrapper class by its class name.

        Args:
            name: The class name (e.g., "MyVPC")

        Returns:
            The wrapper class, or None if not found
        """
        with self._lock:
            return self._resources.get(name)

    def clear(self) -> None:
        """
        Clear the registry.

        Useful for testing to ensure isolation between tests.
        """
        with self._lock:
            self._resources.clear()
            self._by_type.clear()

    def __len__(self) -> int:
        """Return the number of registered resources."""
        with self._lock:
            return len(self._resources)

    def __contains__(self, name: str) -> bool:
        """Check if a resource with the given name is registered."""
        with self._lock:
            return name in self._resources

    def __repr__(self) -> str:
        with self._lock:
            count = len(self._resources)
        return f"ResourceRegistry({count} resources)"


# Global registry instance
registry = ResourceRegistry()
