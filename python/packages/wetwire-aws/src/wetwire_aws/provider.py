"""
CloudFormation serialization provider.

Implements the core Provider interface for CloudFormation-specific
serialization of references, attributes, and resources.
"""

from __future__ import annotations

from typing import Any, get_type_hints

from graph_refs_dataclasses import Provider, is_attr_ref, is_class_ref

from wetwire_aws.intrinsics.functions import GetAtt, IntrinsicFunction, Ref


class CloudFormationProvider(Provider):
    """
    CloudFormation-specific serialization provider.

    Converts graph-refs Ref[T] and Attr[T, name] annotations to
    CloudFormation intrinsic functions {"Ref": "..."} and
    {"Fn::GetAtt": ["...", "..."]}.

    Example:
        >>> provider = CloudFormationProvider()
        >>> provider.serialize_ref(MyFunction, MyBucket)
        {'Ref': 'MyBucket'}
        >>> provider.serialize_attr(MyFunction, MyRole, 'Arn')
        {'Fn::GetAtt': ['MyRole', 'Arn']}
    """

    name = "cloudformation"

    def serialize_ref(
        self,
        source: type[Any],
        target: type[Any],
    ) -> dict[str, str]:
        """
        Serialize a Ref[T] to CloudFormation {"Ref": "LogicalId"}.

        Args:
            source: The referencing wrapper class
            target: The referenced wrapper class

        Returns:
            CloudFormation Ref intrinsic: {"Ref": "TargetClassName"}
        """
        logical_id = self.get_logical_id(target)
        return Ref(logical_id).to_dict()

    def serialize_attr(
        self,
        source: type[Any],
        target: type[Any],
        attr_name: str,
    ) -> dict[str, list[str]]:
        """
        Serialize an Attr[T, name] to CloudFormation {"Fn::GetAtt": [...]}.

        Args:
            source: The referencing wrapper class
            target: The referenced wrapper class
            attr_name: The attribute to retrieve (e.g., "Arn")

        Returns:
            CloudFormation GetAtt intrinsic: {"Fn::GetAtt": ["Target", "Arn"]}
        """
        logical_id = self.get_logical_id(target)
        return GetAtt(logical_id, attr_name).to_dict()

    def serialize_resource(
        self,
        resource: Any,
    ) -> dict[str, Any]:
        """
        Serialize a wrapper resource to CloudFormation format.

        Extracts the resource type from the 'resource' annotation and
        builds the CloudFormation resource definition.

        Args:
            resource: The wrapper resource instance

        Returns:
            CloudFormation resource dict with Type and Properties
        """
        wrapper_cls = type(resource)

        # Get resource type from 'resource' annotation
        try:
            hints = get_type_hints(wrapper_cls)
            resource_type_cls = hints.get("resource")
        except Exception:
            annotations = getattr(wrapper_cls, "__annotations__", {})
            resource_type_cls = annotations.get("resource")

        has_resource_type = hasattr(resource_type_cls, "_resource_type")
        if resource_type_cls is None or not has_resource_type:
            raise ValueError(
                f"Wrapper class {wrapper_cls.__name__} must have a 'resource' "
                "annotation pointing to a CloudFormationResource subclass"
            )

        # Get the AWS resource type string
        cf_type = resource_type_cls._resource_type

        # Build properties from wrapper instance
        properties = self._build_properties(resource, resource_type_cls)

        return {
            "Type": cf_type,
            "Properties": properties,
        }

    def _build_properties(
        self,
        wrapper_instance: Any,
        resource_type_cls: type[Any],
    ) -> dict[str, Any]:
        """
        Build CloudFormation properties from a wrapper instance.

        Args:
            wrapper_instance: The wrapper resource instance
            resource_type_cls: The resource type class

        Returns:
            Dict of CloudFormation properties (PascalCase keys)
        """
        from wetwire_aws.intrinsics.refs import resolve_refs_from_annotations

        # Collect non-private, non-None attributes
        props: dict[str, Any] = {}
        for name, value in wrapper_instance.__dict__.items():
            if name.startswith("_") or name == "resource" or value is None:
                continue

            # Handle no-parens pattern: runtime AttrRef markers
            if is_attr_ref(value):
                # MyRole.Arn -> {"Fn::GetAtt": ["MyRole", "Arn"]}
                props[name] = GetAtt(value.target.__name__, value.attr)
            # Handle no-parens pattern: class references
            elif is_class_ref(value):
                # MyBucket -> {"Ref": "MyBucket"}
                props[name] = Ref(value.__name__)
            elif isinstance(value, type) and hasattr(value, "_refs_marker"):
                # Fallback for refs classes without explicit is_class_ref
                props[name] = Ref(value.__name__)
            else:
                props[name] = value

        # Resolve graph-refs annotations to intrinsics (for type annotation pattern)
        resolved_refs = resolve_refs_from_annotations(wrapper_instance)
        for field_name, ref_value in resolved_refs.items():
            # Only use annotation-based resolution if not already resolved
            if field_name not in props:
                props[field_name] = ref_value

        # Create resource instance and serialize
        resource_instance = resource_type_cls(**props)

        # Use the resource's to_dict() for proper serialization
        result = resource_instance.to_dict()

        # Return just the Properties portion
        properties: dict[str, Any] = result.get("Properties", {})
        return properties

    def _serialize_value(self, value: Any) -> Any:
        """
        Recursively serialize a value for CloudFormation.

        Args:
            value: The value to serialize

        Returns:
            Serialized value suitable for CloudFormation JSON
        """
        # Handle no-parens pattern: AttrRef markers
        if is_attr_ref(value):
            return GetAtt(value.target.__name__, value.attr).to_dict()
        # Handle no-parens pattern: class references
        if is_class_ref(value):
            return Ref(value.__name__).to_dict()
        if isinstance(value, type) and hasattr(value, "_refs_marker"):
            return Ref(value.__name__).to_dict()
        if isinstance(value, IntrinsicFunction):
            return value.to_dict()
        if hasattr(value, "to_dict"):
            return value.to_dict()
        if isinstance(value, list):
            return [self._serialize_value(item) for item in value]
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        return value
