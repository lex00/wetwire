"""
The @wetwire_aws decorator.

This decorator uses dataclass-dsl to create a CloudFormation-specific
decorator with automatic resource registration.
"""

from typing import Any

from dataclass_dsl import ResourceRegistry, create_decorator

# AWS-specific registry for CloudFormation resources
cf_registry = ResourceRegistry()


def _get_resource_type(cls: type[Any]) -> type[Any] | str | None:
    """Extract CF resource type from the 'resource' annotation."""
    annotations = getattr(cls, "__annotations__", {})
    resource_type = annotations.get("resource")
    if resource_type is not None:
        # Return the CF resource type string if available
        return getattr(resource_type, "_resource_type", None)
    return None


# Create the @wetwire_aws decorator using the factory
wetwire_aws = create_decorator(
    registry=cf_registry,
    resource_field="resource",
    get_resource_type=_get_resource_type,
)


def get_aws_registry() -> ResourceRegistry:
    """Get the AWS resource registry.

    Returns:
        The global ResourceRegistry instance containing all classes
        decorated with @wetwire_aws.
    """
    return cf_registry
