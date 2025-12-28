"""
Reference helpers for the wetwire pattern.

This module provides:
1. Re-exports of dataclass-dsl types (Ref, Attr, RefList, etc.) for annotations
2. Helper functions ref() and get_att() for explicit reference creation
3. Serialization support for dataclass-dsl types to CloudFormation intrinsics
"""

from __future__ import annotations

from typing import Any

from dataclass_dsl import (
    Attr,
    ContextRef,
    Ref,
    RefDict,
    RefInfo,
    RefList,
    get_dependencies,
    get_refs,
)

from wetwire_aws.intrinsics.functions import GetAtt
from wetwire_aws.intrinsics.functions import Ref as RefIntrinsic

__all__ = [
    # Re-exported from dataclass-dsl
    "Ref",
    "Attr",
    "RefList",
    "RefDict",
    "ContextRef",
    "RefInfo",
    "get_refs",
    "get_dependencies",
    # Local exports
    "ref",
    "get_att",
    "ARN",
    "Attributes",
    "DeferredRef",
    "DeferredGetAtt",
    "resolve_refs_from_annotations",
]


def ref(resource_class: type | None = None) -> RefIntrinsic | DeferredRef:
    """
    Create a reference to another resource.

    Supports two patterns:

    1. Direct class reference (simple):
        bucket_ref = ref(MyBucket)

    2. Annotation-based (enables dataclass-dsl introspection):
        bucket: Annotated[MyBucket, Ref()] = ref()  # Resolved from type annotation

    The ref() function generates a CloudFormation {"Ref": "LogicalName"} reference.

    Args:
        resource_class: Optional resource class to reference directly.
            If None, the reference is deferred and resolved from type annotation.

    Returns:
        RefIntrinsic if resource_class provided, DeferredRef otherwise.
    """
    if resource_class is not None:
        # Direct pattern: ref(MyBucket)
        return RefIntrinsic(resource_class.__name__)
    else:
        # Annotation pattern: bucket: Ref[MyBucket] = ref()
        return DeferredRef()


def get_att(
    resource_class_or_attr: type | str, attribute: str | None = None
) -> GetAtt | DeferredGetAtt:
    """
    Get an attribute from a resource.

    Supports two patterns:

    1. Direct class reference:
        role_arn = get_att(MyRole, "Arn")
        role_arn = get_att(MyRole, ARN)  # Using constant

    2. Annotation-based (enables dataclass-dsl introspection):
        role_arn: Annotated[str, Attr(MyRole, "Arn")] = get_att("Arn")

    The get_att() function generates a CloudFormation
    {"Fn::GetAtt": ["LogicalName", "Attribute"]} reference.

    Args:
        resource_class_or_attr: Resource class for direct pattern, or
            attribute name string for annotation pattern.
        attribute: Attribute name when using direct pattern.
            None for annotation pattern.

    Returns:
        GetAtt if both class and attribute provided, DeferredGetAtt otherwise.
    """
    if attribute is not None:
        # Direct pattern: get_att(MyRole, "Arn")
        if isinstance(resource_class_or_attr, type):
            return GetAtt(resource_class_or_attr.__name__, attribute)
        else:
            return GetAtt(resource_class_or_attr, attribute)
    else:
        # Annotation pattern: role_arn: Attr[MyRole, "Arn"] = get_att("Arn")
        return DeferredGetAtt(str(resource_class_or_attr))


class DeferredRef:
    """
    A deferred Ref that resolves from type annotation at serialization time.

    Used with the annotation pattern:
        bucket: Annotated[MyBucket, Ref()] = ref()

    The logical_id is resolved from the Annotated[T, Ref()] type annotation.

    Args:
        logical_id: The logical ID to reference. Initially None, set during
            resolution from type annotations.
    """

    def __init__(self, logical_id: str | None = None):
        self.logical_id = logical_id

    def to_dict(self) -> dict[str, str]:
        """Convert to CloudFormation Ref dict.

        Returns:
            Dict with {"Ref": logical_id} structure.

        Raises:
            ValueError: If logical_id has not been set.
        """
        if self.logical_id is None:
            raise ValueError(
                "DeferredRef.logical_id must be set before serialization. "
                "For annotation-based refs (bucket: Annotated[Bucket, Ref()] = ref()),"
                "use resolve_deferred_refs() before serialization."
            )
        return {"Ref": self.logical_id}

    def resolve(self, logical_id: str) -> RefIntrinsic:
        """Resolve to a concrete Ref intrinsic.

        Args:
            logical_id: The logical name of the resource to reference.

        Returns:
            A concrete RefIntrinsic with the given logical_id.
        """
        return RefIntrinsic(logical_id)


class DeferredGetAtt:
    """
    A deferred GetAtt that resolves from type annotation at serialization time.

    Used with the annotation pattern:
        role_arn: Annotated[str, Attr(MyRole, "Arn")] = get_att("Arn")

    The logical_id is resolved from the Annotated[str, Attr(T, "name")] type annotation.

    Args:
        attribute_name: The name of the attribute to get (e.g., "Arn").
        logical_id: The logical ID of the resource. Initially None, set during
            resolution from type annotations.
    """

    def __init__(self, attribute_name: str, logical_id: str | None = None):
        self.attribute_name = attribute_name
        self.logical_id = logical_id

    def to_dict(self) -> dict[str, list[str]]:
        """Convert to CloudFormation Fn::GetAtt dict.

        Returns:
            Dict with {"Fn::GetAtt": [logical_id, attribute_name]} structure.

        Raises:
            ValueError: If logical_id has not been set.
        """
        if self.logical_id is None:
            raise ValueError(
                "DeferredGetAtt.logical_id must be set before serialization. "
                "For annotation-based refs (arn: Annotated[str, Attr(Role, 'Arn')] = get_att('Arn')),"
                "use resolve_deferred_refs() before serialization."
            )
        return {"Fn::GetAtt": [self.logical_id, self.attribute_name]}

    def resolve(self, logical_id: str) -> GetAtt:
        """Resolve to a concrete GetAtt intrinsic.

        Args:
            logical_id: The logical name of the resource.

        Returns:
            A concrete GetAtt with the given logical_id and attribute_name.
        """
        return GetAtt(logical_id, self.attribute_name)


def resolve_refs_from_annotations(wrapper_instance: Any) -> dict[str, Any]:
    """
    Resolve dataclass-dsl type annotations to CloudFormation intrinsics.

    Uses dataclass-dsl's get_refs() to introspect the class and resolves:
    - Annotated[T, Ref()] -> {"Ref": "T"}
    - Annotated[str, Attr(T, "name")] -> {"Fn::GetAtt": ["T", "name"]}
    - Annotated[list[T], RefList()] -> [{"Ref": "T"}] (list of refs)
    - Annotated[str, ContextRef("name")] -> {"Ref": "name"} (for pseudo-parameters)

    Args:
        wrapper_instance: An instance of a wrapper class

    Returns:
        Dict of field names to resolved intrinsic values
    """
    wrapper_cls = type(wrapper_instance)
    resolved: dict[str, Any] = {}

    # Use dataclass-dsl introspection
    refs = get_refs(wrapper_cls)

    for field_name, ref_info in refs.items():
        if field_name == "resource":
            continue

        # Skip if target is not a real class (e.g., type(None) for ContextRef)
        if ref_info.is_context:
            # ContextRef("AWS::Region") -> {"Ref": "AWS::Region"}
            if ref_info.attr:
                resolved[field_name] = RefIntrinsic(ref_info.attr)
        elif ref_info.attr is not None:
            # Attr(MyRole, "Arn") -> {"Fn::GetAtt": ["MyRole", "Arn"]}
            if isinstance(ref_info.target, type):
                resolved[field_name] = GetAtt(ref_info.target.__name__, ref_info.attr)
        elif ref_info.is_list:
            # RefList() - we'll handle this at the value level, not annotation level
            # The actual list values need to be resolved individually
            pass
        elif ref_info.is_dict:
            # RefDict[K, V] - similar to RefList
            pass
        else:
            # Ref() -> {"Ref": "MyBucket"}
            if isinstance(ref_info.target, type):
                resolved[field_name] = RefIntrinsic(ref_info.target.__name__)

    return resolved


# Common attribute constants (top-level for easy import)
ARN = "Arn"


# Common attribute shortcuts (grouped)
class Attributes:
    """Common CloudFormation attribute names."""

    ARN = "Arn"
    ID = "Id"
    DOMAIN_NAME = "DomainName"
    ENDPOINT = "Endpoint"
    NAME = "Name"
    PRIVATE_IP = "PrivateIp"
    PUBLIC_IP = "PublicIp"
    URL = "Url"
    WEBSITE_URL = "WebsiteURL"
