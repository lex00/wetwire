"""
Abstract provider interface for format-specific serialization.

Domain packages (wetwire-aws, wetwire-gcp, etc.) implement this
interface to provide format-specific serialization logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wetwire.template import Template


class Provider(ABC):
    """
    Abstract provider for format-specific serialization.

    Subclasses implement domain-specific serialization logic:
    - CloudFormationProvider: {"Ref": "LogicalId"}
    - KubernetesProvider: name: resource-name
    - TerraformProvider: module.resource_name.id

    Example:
        >>> class CloudFormationProvider(Provider):
        ...     name = "cloudformation"
        ...
        ...     def serialize_ref(self, source, target):
        ...         return {"Ref": target.__name__}
        ...
        ...     def serialize_attr(self, source, target, attr_name):
        ...         return {"Fn::GetAtt": [target.__name__, attr_name]}
        ...
        ...     def serialize_resource(self, resource):
        ...         return {
        ...             "Type": resource.resource.resource_type,
        ...             "Properties": resource.resource.to_dict(),
        ...         }
    """

    name: str  # Provider identifier (e.g., "cloudformation", "kubernetes")

    @abstractmethod
    def serialize_ref(
        self,
        source: type[Any],
        target: type[Any],
    ) -> Any:
        """
        Serialize a reference from source to target.

        Args:
            source: The referencing class
            target: The referenced class

        Returns:
            Provider-specific reference representation

        Example (CloudFormation):
            {"Ref": "MyBucket"}

        Example (Kubernetes):
            "my-bucket"
        """
        ...

    @abstractmethod
    def serialize_attr(
        self,
        source: type[Any],
        target: type[Any],
        attr_name: str,
    ) -> Any:
        """
        Serialize an attribute reference.

        Args:
            source: The referencing class
            target: The referenced class
            attr_name: The attribute name

        Returns:
            Provider-specific attribute reference representation

        Example (CloudFormation):
            {"Fn::GetAtt": ["MyRole", "Arn"]}
        """
        ...

    @abstractmethod
    def serialize_resource(
        self,
        resource: Any,
    ) -> dict[str, Any]:
        """
        Serialize a resource to provider format.

        Args:
            resource: The wrapper resource instance

        Returns:
            Provider-specific resource representation
        """
        ...

    def serialize_template(
        self,
        template: Template,
    ) -> dict[str, Any]:
        """
        Serialize a complete template.

        Default implementation builds a dict with serialized resources.
        Override for domain-specific template structure.

        Args:
            template: The Template to serialize

        Returns:
            Provider-specific template representation
        """
        resources: dict[str, Any] = {}
        for resource in template.get_dependency_order():
            logical_id = self.get_logical_id(type(resource))
            resources[logical_id] = self.serialize_resource(resource)

        result: dict[str, Any] = {}
        if template.description:
            result["Description"] = template.description
        if resources:
            result["Resources"] = resources
        if template.parameters:
            result["Parameters"] = template.parameters
        if template.outputs:
            result["Outputs"] = template.outputs
        if template.conditions:
            result["Conditions"] = template.conditions
        if template.mappings:
            result["Mappings"] = template.mappings
        if template.metadata:
            result["Metadata"] = template.metadata

        return result

    def get_logical_id(self, wrapper_cls: type[Any]) -> str:
        """
        Get the logical ID for a wrapper class.

        Args:
            wrapper_cls: The wrapper class

        Returns:
            The logical ID string (default: class name)
        """
        return getattr(wrapper_cls, "_logical_id", wrapper_cls.__name__)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
