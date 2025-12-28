"""
AWS CloudFormation resource loader.

Convenience wrapper around dataclass_dsl.setup_resources with
AWS-specific namespace injection and stub configuration.

Usage in a resources package __init__.py:
    from wetwire_aws.loader import setup_resources
    setup_resources(__file__, __name__, globals())
"""

from __future__ import annotations

from typing import Any

from dataclass_dsl import Attr, Ref, RefDict, RefList
from dataclass_dsl import setup_resources as _setup_resources

from wetwire_aws.stubs import AWS_STUB_CONFIG


def _get_aws_namespace() -> dict[str, Any]:
    """Get the AWS-specific namespace to inject into resource modules.

    This includes all the decorators, types, service modules, and helpers
    that resource files need when using `from . import *`.
    """
    # Import here to avoid circular imports
    from wetwire_aws import resources
    from wetwire_aws.base import CloudFormationResource, PropertyType, Tag
    from wetwire_aws.decorator import wetwire_aws
    from wetwire_aws.intrinsics import ARN, get_att, ref
    from wetwire_aws.intrinsics.functions import (
        And,
        Base64,
        Cidr,
        Equals,
        FindInMap,
        GetAtt,
        GetAZs,
        If,
        ImportValue,
        Join,
        Not,
        Or,
        Select,
        Split,
        Sub,
        Transform,
    )
    from wetwire_aws.intrinsics.functions import Ref as RefIntrinsic
    from wetwire_aws.intrinsics.pseudo import (
        AWS_ACCOUNT_ID,
        AWS_NO_VALUE,
        AWS_NOTIFICATION_ARNS,
        AWS_PARTITION,
        AWS_REGION,
        AWS_STACK_ID,
        AWS_STACK_NAME,
        AWS_URL_SUFFIX,
    )
    from wetwire_aws.template import CloudFormationTemplate

    # Build namespace with all service modules
    namespace: dict[str, Any] = {
        # Decorator
        "wetwire_aws": wetwire_aws,
        # Base classes
        "CloudFormationResource": CloudFormationResource,
        "PropertyType": PropertyType,
        "Tag": Tag,
        # Template
        "CloudFormationTemplate": CloudFormationTemplate,
        # Reference types from dataclass-dsl
        "Ref": Ref,
        "Attr": Attr,
        "RefList": RefList,
        "RefDict": RefDict,
        # Reference helpers
        "ref": ref,
        "get_att": get_att,
        "ARN": ARN,
        # Intrinsic functions (CF intrinsics)
        "RefIntrinsic": RefIntrinsic,
        "GetAtt": GetAtt,
        "Sub": Sub,
        "Join": Join,
        "Select": Select,
        "Split": Split,
        "If": If,
        "Equals": Equals,
        "And": And,
        "Or": Or,
        "Not": Not,
        "Base64": Base64,
        "GetAZs": GetAZs,
        "ImportValue": ImportValue,
        "FindInMap": FindInMap,
        "Transform": Transform,
        "Cidr": Cidr,
        # Pseudo-parameters
        "AWS_ACCOUNT_ID": AWS_ACCOUNT_ID,
        "AWS_NOTIFICATION_ARNS": AWS_NOTIFICATION_ARNS,
        "AWS_NO_VALUE": AWS_NO_VALUE,
        "AWS_PARTITION": AWS_PARTITION,
        "AWS_REGION": AWS_REGION,
        "AWS_STACK_ID": AWS_STACK_ID,
        "AWS_STACK_NAME": AWS_STACK_NAME,
        "AWS_URL_SUFFIX": AWS_URL_SUFFIX,
    }

    # Add all service modules from resources package
    for attr_name in dir(resources):
        if not attr_name.startswith("_"):
            module = getattr(resources, attr_name)
            if hasattr(module, "__file__"):  # It's a module
                namespace[attr_name] = module

    return namespace


def setup_resources(
    init_file: str,
    package_name: str,
    package_globals: dict[str, Any],
    *,
    generate_stubs: bool = True,
) -> None:
    """Set up AWS CloudFormation resource imports.

    Wrapper around dataclass_dsl.setup_resources with AWS-specific
    namespace injection and stub configuration pre-applied.

    This function:
    1. Finds all .py files in the package directory
    2. Parses them to find class definitions and ref()/get_att() calls
    3. Builds a dependency graph from the references
    4. Imports modules in topological order
    5. Injects AWS decorators, types, and service modules into each module's namespace
    6. Generates .pyi stubs with AWS-specific imports for IDE support

    Args:
        init_file: Path to __init__.py (__file__)
        package_name: Package name (__name__)
        package_globals: Package globals dict (globals())
        generate_stubs: Whether to generate .pyi files (default: True)

    Example:
        # In myapp/resources/__init__.py
        from wetwire_aws.loader import setup_resources
        setup_resources(__file__, __name__, globals())
    """
    _setup_resources(
        init_file,
        package_name,
        package_globals,
        stub_config=AWS_STUB_CONFIG,
        generate_stubs=generate_stubs,
        extra_namespace=_get_aws_namespace(),
    )
