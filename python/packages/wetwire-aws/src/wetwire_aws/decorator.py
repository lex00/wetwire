"""
The @wetwire_aws decorator.

This decorator wraps the core @wetwire decorator with AWS-specific
defaults and registration.
"""

from typing import TypeVar

from wetwire import wetwire
from wetwire.registry import ResourceRegistry

T = TypeVar("T")

# AWS-specific registry
_aws_registry = ResourceRegistry()


def wetwire_aws(cls: type[T]) -> type[T]:
    """
    Decorator for AWS CloudFormation resources.

    Transforms a class into a dataclass and registers it with the AWS resource
    registry for template generation.

    Args:
        cls: The class to decorate. Must have a 'resource' annotation pointing
            to a CloudFormationResource subclass.

    Returns:
        The decorated class, now a dataclass registered with the AWS registry.

    Example:
        >>> @wetwire_aws
        ... class MyBucket:
        ...     resource: s3.Bucket
        ...     bucket_name = "my-bucket"
    """
    # Apply the core wetwire decorator
    decorated = wetwire(cls)

    # Get the resource type from annotations
    annotations = getattr(cls, "__annotations__", {})
    resource_type = annotations.get("resource")

    if resource_type is not None:
        # Register with resource type
        resource_type_str = getattr(resource_type, "_resource_type", "")
        _aws_registry.register(decorated, resource_type_str)
    else:
        # Register without resource type (might be a property type)
        _aws_registry.register(decorated, "")

    return decorated


def get_aws_registry() -> ResourceRegistry:
    """Get the AWS resource registry.

    Returns:
        The global ResourceRegistry instance containing all classes
        decorated with @wetwire_aws.
    """
    return _aws_registry
