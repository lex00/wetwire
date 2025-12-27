"""
Base classes for CloudFormation resources.

CloudFormationResource is the base class for all AWS resource types.
PropertyType is the base class for nested property structures.
"""

from dataclasses import dataclass, field
from typing import Any, ClassVar


def _serialize_value(value: Any) -> Any:
    """Recursively serialize a value for CloudFormation JSON.

    Args:
        value: The value to serialize. Can be a primitive, list, dict,
            or object with a to_dict() method.

    Returns:
        The serialized value suitable for CloudFormation JSON output.
    """
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    return value


def _to_cf_name(snake_name: str) -> str:
    """Convert snake_case to PascalCase for CloudFormation.

    Args:
        snake_name: A snake_case property name (e.g., "bucket_name").
            Trailing underscores are stripped to handle Python keyword escapes.

    Returns:
        PascalCase string (e.g., "BucketName").
    """
    # Strip trailing underscore (used for Python keyword escape)
    if snake_name.endswith("_") and not snake_name.endswith("__"):
        snake_name = snake_name[:-1]
    return "".join(word.capitalize() for word in snake_name.split("_"))


@dataclass
class PropertyType:
    """
    Base class for CloudFormation property types (nested structures).

    Property types represent complex nested properties within resources,
    such as S3 Bucket's VersioningConfiguration or EC2 Instance's BlockDeviceMapping.
    """

    def to_dict(self) -> dict[str, Any]:
        """Convert property to CloudFormation-compatible dict.

        Transforms all instance attributes to PascalCase keys and recursively
        serializes nested values. None values and empty collections are omitted.

        Returns:
            Dict with PascalCase keys suitable for CloudFormation JSON.
        """
        result: dict[str, Any] = {}

        for prop_name, prop_value in self.__dict__.items():
            if prop_value is None:
                continue
            if prop_name.startswith("_"):
                continue
            # Skip empty lists and dicts (they're just default values)
            if isinstance(prop_value, (list, dict)) and len(prop_value) == 0:
                continue

            # Convert to CloudFormation property name (snake_case to PascalCase)
            cf_name = _to_cf_name(prop_name)
            result[cf_name] = _serialize_value(prop_value)

        return result


@dataclass
class CloudFormationResource:
    """
    Base class for all CloudFormation resource types.

    Subclasses must define:
    - _resource_type: The AWS resource type (e.g., "AWS::S3::Bucket")

    Optional class variables:
    - _property_mappings: Dict mapping Python names to CF property names
    """

    _resource_type: ClassVar[str] = ""
    _property_mappings: ClassVar[dict[str, str]] = {}

    # Optional resource metadata (kw_only to allow subclasses to have required fields)
    depends_on: list[type] | None = field(default=None, repr=False, kw_only=True)
    condition: str | None = field(default=None, repr=False, kw_only=True)
    metadata: dict[str, Any] | None = field(default=None, repr=False, kw_only=True)
    deletion_policy: str | None = field(default=None, repr=False, kw_only=True)
    update_policy: dict[str, Any] | None = field(default=None, repr=False, kw_only=True)
    update_replace_policy: str | None = field(default=None, repr=False, kw_only=True)

    def to_dict(self) -> dict[str, Any]:
        """Convert resource to CloudFormation-compatible dict.

        Generates a complete CloudFormation resource definition including
        Type, Properties, and optional metadata fields (DependsOn, Condition, etc.).

        Returns:
            Dict with CloudFormation resource structure:
            {"Type": "AWS::...", "Properties": {...}, ...}
        """
        properties: dict[str, Any] = {}

        # Get all fields that are actual properties (not metadata)
        metadata_fields = {
            "depends_on",
            "condition",
            "metadata",
            "deletion_policy",
            "update_policy",
            "update_replace_policy",
        }

        for prop_name, prop_value in self.__dict__.items():
            if prop_value is None:
                continue
            if prop_name.startswith("_"):
                continue
            if prop_name in metadata_fields:
                continue
            # Skip empty lists and dicts (they're just default values)
            if isinstance(prop_value, (list, dict)) and len(prop_value) == 0:
                continue

            # Check for explicit property mapping
            if prop_name in self._property_mappings:
                cf_name = self._property_mappings[prop_name]
            else:
                cf_name = _to_cf_name(prop_name)

            # Serialize the value (handles PropertyTypes, IntrinsicFunctions, etc.)
            properties[cf_name] = _serialize_value(prop_value)

        result: dict[str, Any] = {
            "Type": self._resource_type,
            "Properties": properties,
        }

        # Add optional metadata fields
        if self.depends_on:
            result["DependsOn"] = [cls.__name__ for cls in self.depends_on]
        if self.condition:
            result["Condition"] = self.condition
        if self.metadata:
            result["Metadata"] = self.metadata
        if self.deletion_policy:
            result["DeletionPolicy"] = self.deletion_policy
        if self.update_policy:
            result["UpdatePolicy"] = self.update_policy
        if self.update_replace_policy:
            result["UpdateReplacePolicy"] = self.update_replace_policy

        return result

    @classmethod
    def get_resource_type(cls) -> str:
        """Return the AWS resource type string.

        Returns:
            The CloudFormation resource type (e.g., "AWS::S3::Bucket").
        """
        return cls._resource_type
