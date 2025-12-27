"""
Template base class for resource aggregation.

Collects resources from the registry and provides serialization
to various output formats via providers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from wetwire.ordering import get_creation_order
from wetwire.registry import registry

if TYPE_CHECKING:
    from wetwire.context import Context
    from wetwire.provider import Provider


@dataclass
class Template:
    """
    Base template class for resource aggregation.

    Collects resources and provides serialization to target formats.

    Example:
        >>> # Build template from registry
        >>> template = Template.from_registry(
        ...     description="My infrastructure",
        ...     scope_package="myproject.resources",
        ... )
        >>>
        >>> # Serialize with a provider
        >>> from wetwire_aws import CloudFormationProvider
        >>> output = template.to_json(provider=CloudFormationProvider())

    Attributes:
        description: Template description
        resources: List of resource instances
        parameters: Template parameters
        outputs: Template outputs
        conditions: Template conditions
        mappings: Template mappings
        metadata: Template metadata
    """

    description: str = ""
    resources: list[Any] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    conditions: dict[str, Any] = field(default_factory=dict)
    mappings: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_registry(
        cls,
        description: str = "",
        scope_package: str | None = None,
        context: Context | None = None,
        **kwargs: Any,
    ) -> Template:
        """
        Build a template from registered resources.

        Creates instances of all registered wrapper classes and
        aggregates them into a template.

        Args:
            description: Template description
            scope_package: Only include resources from this package prefix
            context: Context for resolving context references
            **kwargs: Additional template attributes

        Returns:
            A Template containing all matching resources

        Example:
            >>> template = Template.from_registry(
            ...     description="Production stack",
            ...     scope_package="myproject.prod",
            ... )
        """
        wrapper_classes = registry.get_all(scope_package=scope_package)

        # Instantiate all wrapper classes
        resources = []
        for wrapper_cls in wrapper_classes:
            try:
                instance = wrapper_cls()
                resources.append(instance)
            except Exception as e:
                # Log but don't fail - some classes might need special handling
                import warnings

                warnings.warn(
                    f"Failed to instantiate {wrapper_cls.__name__}: {e}",
                    stacklevel=2,
                )

        return cls(
            description=description,
            resources=resources,
            **kwargs,
        )

    def add_resource(self, resource: Any) -> None:
        """
        Add a resource to the template.

        Args:
            resource: A wrapper resource instance
        """
        self.resources.append(resource)

    def get_dependency_order(self) -> list[Any]:
        """
        Return resources in dependency order.

        Dependencies appear before dependents.

        Returns:
            List of resources sorted by dependencies
        """
        if not self.resources:
            return []

        # Get the classes and their order
        classes = [type(r) for r in self.resources]
        ordered_classes = get_creation_order(classes)

        # Map instances to their class for reordering
        class_to_instance = {type(r): r for r in self.resources}

        return [
            class_to_instance[cls]
            for cls in ordered_classes
            if cls in class_to_instance
        ]

    def to_dict(self, provider: Provider | None = None) -> dict[str, Any]:
        """
        Serialize template to dictionary format.

        Args:
            provider: Provider for format-specific serialization.
                     If None, returns a generic dict structure.

        Returns:
            Dict representation of the template
        """
        if provider is not None:
            return provider.serialize_template(self)

        # Generic dict format
        result: dict[str, Any] = {}
        if self.description:
            result["description"] = self.description
        if self.resources:
            result["resources"] = [
                {"class": type(r).__name__, "instance": r}
                for r in self.get_dependency_order()
            ]
        if self.parameters:
            result["parameters"] = self.parameters
        if self.outputs:
            result["outputs"] = self.outputs
        if self.conditions:
            result["conditions"] = self.conditions
        if self.mappings:
            result["mappings"] = self.mappings
        if self.metadata:
            result["metadata"] = self.metadata

        return result

    def to_json(
        self,
        provider: Provider | None = None,
        indent: int = 2,
    ) -> str:
        """
        Serialize template to JSON string.

        Args:
            provider: Provider for format-specific serialization
            indent: JSON indentation level

        Returns:
            JSON string representation
        """
        data = self.to_dict(provider=provider)

        # Custom encoder to handle non-serializable objects
        def default_encoder(obj: Any) -> Any:
            if hasattr(obj, "to_dict"):
                return obj.to_dict()
            if hasattr(obj, "__dict__"):
                return obj.__dict__
            return str(obj)

        return json.dumps(data, indent=indent, default=default_encoder)

    def to_yaml(self, provider: Provider | None = None) -> str:
        """
        Serialize template to YAML string.

        Requires PyYAML to be installed.

        Args:
            provider: Provider for format-specific serialization

        Returns:
            YAML string representation

        Raises:
            ImportError: If PyYAML is not installed
        """
        try:
            import yaml
        except ImportError as e:
            raise ImportError(
                "PyYAML is required for YAML output. Install with: pip install pyyaml"
            ) from e

        data = self.to_dict(provider=provider)
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    def validate(self) -> list[str]:
        """
        Validate template structure.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        # Check for duplicate resource names
        names = [type(r).__name__ for r in self.resources]
        duplicates = [name for name in set(names) if names.count(name) > 1]
        if duplicates:
            errors.append(f"Duplicate resource names: {duplicates}")

        return errors

    def __len__(self) -> int:
        """Return the number of resources in the template."""
        return len(self.resources)

    def __repr__(self) -> str:
        return f"Template(description={self.description!r}, resources={len(self)})"
