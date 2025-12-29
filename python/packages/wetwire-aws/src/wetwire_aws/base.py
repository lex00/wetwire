"""
Base classes for CloudFormation resources.

CloudFormationResource is the base class for all AWS resource types.
PropertyType is the base class for nested property structures.
Context is the base class for environment-specific configuration.
"""

from dataclasses import dataclass, field
from typing import Annotated, Any, ClassVar

from dataclass_dsl import ContextRef, is_attr_ref, is_class_ref
from dataclass_dsl import PropertyType as PropertyTypeBase
from dataclass_dsl import Resource
from dataclass_dsl._loader import _ClassPlaceholder


def _is_property_type_wrapper(cls: type) -> bool:
    """Check if a class is a PropertyType wrapper (not a Resource wrapper).

    PropertyType wrappers have a `resource` annotation pointing to a PropertyType
    subclass. Resource wrappers point to CloudFormationResource subclasses.

    Args:
        cls: The class to check.

    Returns:
        True if the class wraps a PropertyType, False otherwise.
    """
    annotations = getattr(cls, "__annotations__", {})
    resource_type = annotations.get("resource")
    if resource_type is None:
        return False
    # Check if resource_type is a PropertyType (not a CloudFormationResource)
    # PropertyType doesn't have _resource_type, CloudFormationResource does
    return not hasattr(resource_type, "_resource_type")


def _instantiate_property_type_wrapper(wrapper_cls: type) -> Any:
    """Create a PropertyType instance from a wrapper class.

    Wrapper classes have a `resource:` annotation pointing to a PropertyType
    subclass. This function extracts the property values from the wrapper
    and creates an actual PropertyType instance.

    Args:
        wrapper_cls: A class with `resource: SomePropertyType` annotation.

    Returns:
        An instance of the PropertyType with values from the wrapper.
    """
    # Get the PropertyType class from the wrapper's annotation
    annotations = getattr(wrapper_cls, "__annotations__", {})
    property_type_cls = annotations.get("resource")
    if property_type_cls is None:
        # Shouldn't happen if _is_property_type_wrapper was True
        return None

    # Create wrapper instance to get its property values
    wrapper_instance = wrapper_cls()

    # Collect properties from wrapper (excluding 'resource' and private attrs)
    props: dict[str, Any] = {}
    for k, v in wrapper_instance.__dict__.items():
        if k.startswith("_") or k == "resource" or v is None:
            continue
        # Recursively serialize nested values (handles nested wrappers, lists, etc.)
        props[k] = _serialize_value(v)

    # Create and return the PropertyType instance
    # Use to_dict() on the PropertyType instance
    property_instance = property_type_cls(**props)
    return property_instance


def _serialize_value(value: Any) -> Any:
    """Recursively serialize a value for CloudFormation JSON.

    Args:
        value: The value to serialize. Can be a primitive, list, dict,
            or object with a to_dict() method.

    Returns:
        The serialized value suitable for CloudFormation JSON output.
    """
    # Handle unresolved placeholders (should be resolved by loader, but handle gracefully)
    if isinstance(value, _ClassPlaceholder):
        from wetwire_aws.intrinsics import Ref

        return Ref(value._name).to_dict()
    # Handle no-parens pattern: AttrRef markers (e.g., MyRole.Arn)
    if is_attr_ref(value):
        from wetwire_aws.intrinsics import GetAtt

        return GetAtt(value.target.__name__, value.attr).to_dict()
    # Handle no-parens pattern: class references (e.g., MyBucket)
    if is_class_ref(value):
        # Check if this is a PropertyType wrapper - if so, instantiate and serialize
        if _is_property_type_wrapper(value):
            property_instance = _instantiate_property_type_wrapper(value)
            if property_instance is not None and hasattr(property_instance, "to_dict"):
                return property_instance.to_dict()
        # Otherwise it's a Resource wrapper - serialize as Ref
        from wetwire_aws.intrinsics import Ref

        return Ref(value.__name__).to_dict()
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
class PropertyType(PropertyTypeBase):
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
class Tag(PropertyType):
    """
    Standard AWS resource tag.

    Most AWS resources support tagging via a list of Tag objects.
    This is defined centrally to avoid generating 200+ identical copies.

    Example:
        >>> tags = [Tag(key="Environment", value="Production")]
    """

    key: str | None = None
    value: str | None = None


@dataclass
class PolicyStatement:
    """
    IAM Policy Statement for use with the wrapper dataclass pattern.

    This class allows you to define IAM policy statements as separate
    dataclasses that can be referenced by PolicyDocument and Role resources.

    Note: Uses 'resource_arn' instead of 'resource' to avoid conflicts
    with the wrapper pattern's 'resource:' type annotation field.

    Example:
        @wetwire_aws
        class AllowS3ReadStatement:
            resource: PolicyStatement
            action = ["s3:GetObject", "s3:ListBucket"]
            resource_arn = [MyBucket.Arn, Sub("${MyBucket.Arn}/*")]

        @wetwire_aws
        class MyPolicy:
            resource: PolicyDocument
            statement = [AllowS3ReadStatement]
    """

    sid: str | None = None
    effect: str = "Allow"
    principal: Any = None
    action: Any = None
    resource_arn: Any = None
    condition: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize statement to IAM policy format."""
        stmt: dict[str, Any] = {"Effect": self.effect}

        if self.sid:
            stmt["Sid"] = self.sid
        if self.principal is not None:
            stmt["Principal"] = _serialize_value(self.principal)
        if self.action is not None:
            stmt["Action"] = _serialize_value(self.action)
        if self.resource_arn is not None:
            stmt["Resource"] = _serialize_value(self.resource_arn)
        if self.condition is not None:
            stmt["Condition"] = _serialize_value(self.condition)

        return stmt


@dataclass
class DenyStatement(PolicyStatement):
    """
    IAM Deny Policy Statement.

    Subclass of PolicyStatement with effect pre-set to "Deny".

    Example:
        @wetwire_aws
        class DenyDeleteStatement:
            resource: DenyStatement
            action = ["s3:DeleteObject", "s3:DeleteBucket"]
            resource_arn = "*"
    """

    effect: str = "Deny"


@dataclass
class PolicyDocument:
    """
    IAM Policy Document for use with the wrapper dataclass pattern.

    This class allows you to define IAM policy documents as separate
    dataclasses that can be referenced by Role resources.

    Example:
        @wetwire_aws
        class AssumeRolePolicy:
            resource: PolicyDocument
            statement = [AllowAssumeRoleStatement]

        @wetwire_aws
        class MyRole:
            resource: iam.Role
            assume_role_policy_document = AssumeRolePolicy
    """

    version: str = "2012-10-17"
    statement: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize policy document to IAM format."""
        return {
            "Version": self.version,
            "Statement": [
                s.to_dict() if hasattr(s, "to_dict") else s for s in self.statement
            ],
        }


@dataclass
class CloudFormationResource(Resource):
    """
    Base class for all CloudFormation resource types.

    Subclasses must define:
    - _resource_type: The AWS resource type (e.g., "AWS::S3::Bucket")

    Optional class variables:
    - _property_mappings: Dict mapping Python names to CF property names
    """

    _resource_type: ClassVar[str] = ""
    _property_mappings: ClassVar[dict[str, str]] = {}
    # Alias for consistency with base Resource class
    resource_type: ClassVar[str] = ""

    # Optional resource metadata (kw_only to allow subclasses to have required fields)
    depends_on: list[type] | None = field(default=None, repr=False, kw_only=True)
    condition: str | None = field(default=None, repr=False, kw_only=True)
    metadata: dict[str, Any] | None = field(default=None, repr=False, kw_only=True)
    deletion_policy: str | None = field(default=None, repr=False, kw_only=True)
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
            result["DependsOn"] = [
                dep if isinstance(dep, str) else dep.__name__
                for dep in self.depends_on
            ]
        if self.condition:
            result["Condition"] = self.condition
        if self.metadata:
            result["Metadata"] = self.metadata
        if self.deletion_policy:
            result["DeletionPolicy"] = self.deletion_policy
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


@dataclass
class Context:
    """
    Base context for environment-specific values.

    Subclass to add domain-specific values:

        @dataclass
        class AWSContext(Context):
            account_id: str = ""
            region: str = ""
            stack_name: str = ""

    Example:
        >>> ctx = Context(project="myapp", environment="production")
        >>> ctx.get("project")
        'myapp'
    """

    project: str = ""
    environment: str = ""

    def get(self, name: str, default: Any = None) -> Any:
        """
        Get a context value by name.

        Args:
            name: The context value name
            default: Default value if not found

        Returns:
            The context value or default
        """
        return getattr(self, name, default)

    def resolve(self, context_ref: object) -> Any:
        """
        Resolve a ContextRef to its value.

        Args:
            context_ref: The context reference to resolve

        Returns:
            The resolved value
        """
        # Extract the name from the ContextRef
        # ContextRef["name"] has the name as the type argument
        args = getattr(context_ref, "__args__", ())
        if args:
            name = args[0]
            if isinstance(name, str):
                return self.get(name)
        return None


# Type aliases for common context references
# These are used as type annotations: field: PROJECT
PROJECT = Annotated[str, ContextRef("project")]
ENVIRONMENT = Annotated[str, ContextRef("environment")]
