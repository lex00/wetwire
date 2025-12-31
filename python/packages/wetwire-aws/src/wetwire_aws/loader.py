"""
AWS CloudFormation resource loader.

Convenience wrapper around dataclass_dsl.setup_resources with
AWS-specific namespace injection and stub configuration.

Usage in a resources package __init__.py:
    from wetwire_aws.loader import setup_params, setup_resources

    setup_params(globals())  # Inject Parameter, STRING, wetwire_aws, etc.

    from .params import *  # noqa: F403, F401

    setup_resources(__file__, __name__, globals())

    from .outputs import *  # noqa: F403, F401
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
    from wetwire_aws.base import (
        CloudFormationResource,
        DenyStatement,
        PolicyDocument,
        PolicyStatement,
        PropertyType,
        Tag,
    )
    from wetwire_aws.constants import (
        ARN_EQUALS,
        ARN_LIKE,
        ARN_NOT_EQUALS,
        ARN_NOT_LIKE,
        BOOL,
        DATE_EQUALS,
        DATE_GREATER_THAN,
        DATE_GREATER_THAN_EQUALS,
        DATE_LESS_THAN,
        DATE_LESS_THAN_EQUALS,
        DATE_NOT_EQUALS,
        IP_ADDRESS,
        NOT_IP_ADDRESS,
        NULL,
        NUMERIC_EQUALS,
        NUMERIC_GREATER_THAN,
        NUMERIC_GREATER_THAN_EQUALS,
        NUMERIC_LESS_THAN,
        NUMERIC_LESS_THAN_EQUALS,
        NUMERIC_NOT_EQUALS,
        STRING_EQUALS,
        STRING_EQUALS_IGNORE_CASE,
        STRING_LIKE,
        STRING_NOT_EQUALS,
        STRING_NOT_EQUALS_IGNORE_CASE,
        STRING_NOT_LIKE,
    )
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
    from wetwire_aws.intrinsics.functions import Condition as ConditionIntrinsic
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
    from wetwire_aws.params import (
        AMI_ID,
        AVAILABILITY_ZONE,
        COMMA_DELIMITED_LIST,
        HOSTED_ZONE_ID,
        INSTANCE_ID,
        KEY_PAIR,
        LIST_AVAILABILITY_ZONE,
        LIST_NUMBER,
        LIST_SECURITY_GROUP_ID,
        LIST_SUBNET_ID,
        NUMBER,
        SECURITY_GROUP_ID,
        SSM_PARAMETER_STRING,
        SSM_PARAMETER_STRING_LIST,
        STRING,
        SUBNET_ID,
        VOLUME_ID,
        VPC_ID,
    )
    from wetwire_aws.template import (
        CloudFormationTemplate,
        Mapping,
        Output,
        Parameter,
    )
    from wetwire_aws.template import (
        Condition as TemplateCondition,
    )

    # Build namespace with all service modules
    namespace: dict[str, Any] = {
        # Decorator
        "wetwire_aws": wetwire_aws,
        # Base classes
        "CloudFormationResource": CloudFormationResource,
        "PropertyType": PropertyType,
        "Tag": Tag,
        # Policy helpers
        "PolicyStatement": PolicyStatement,
        "DenyStatement": DenyStatement,
        "PolicyDocument": PolicyDocument,
        # Template and components
        "CloudFormationTemplate": CloudFormationTemplate,
        "Parameter": Parameter,
        "Output": Output,
        "Mapping": Mapping,
        "TemplateCondition": TemplateCondition,  # Renamed to avoid conflict with intrinsic
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
        "Condition": ConditionIntrinsic,  # Intrinsic function for referencing conditions
        # Parameter type constants
        "STRING": STRING,
        "NUMBER": NUMBER,
        "LIST_NUMBER": LIST_NUMBER,
        "COMMA_DELIMITED_LIST": COMMA_DELIMITED_LIST,
        "SSM_PARAMETER_STRING": SSM_PARAMETER_STRING,
        "SSM_PARAMETER_STRING_LIST": SSM_PARAMETER_STRING_LIST,
        "AVAILABILITY_ZONE": AVAILABILITY_ZONE,
        "LIST_AVAILABILITY_ZONE": LIST_AVAILABILITY_ZONE,
        "AMI_ID": AMI_ID,
        "INSTANCE_ID": INSTANCE_ID,
        "KEY_PAIR": KEY_PAIR,
        "SECURITY_GROUP_ID": SECURITY_GROUP_ID,
        "LIST_SECURITY_GROUP_ID": LIST_SECURITY_GROUP_ID,
        "SUBNET_ID": SUBNET_ID,
        "LIST_SUBNET_ID": LIST_SUBNET_ID,
        "VPC_ID": VPC_ID,
        "VOLUME_ID": VOLUME_ID,
        "HOSTED_ZONE_ID": HOSTED_ZONE_ID,
        # Pseudo-parameters
        "AWS_ACCOUNT_ID": AWS_ACCOUNT_ID,
        "AWS_NOTIFICATION_ARNS": AWS_NOTIFICATION_ARNS,
        "AWS_NO_VALUE": AWS_NO_VALUE,
        "AWS_PARTITION": AWS_PARTITION,
        "AWS_REGION": AWS_REGION,
        "AWS_STACK_ID": AWS_STACK_ID,
        "AWS_STACK_NAME": AWS_STACK_NAME,
        "AWS_URL_SUFFIX": AWS_URL_SUFFIX,
        # Condition operator constants
        "BOOL": BOOL,
        "STRING_EQUALS": STRING_EQUALS,
        "STRING_NOT_EQUALS": STRING_NOT_EQUALS,
        "STRING_EQUALS_IGNORE_CASE": STRING_EQUALS_IGNORE_CASE,
        "STRING_NOT_EQUALS_IGNORE_CASE": STRING_NOT_EQUALS_IGNORE_CASE,
        "STRING_LIKE": STRING_LIKE,
        "STRING_NOT_LIKE": STRING_NOT_LIKE,
        "NUMERIC_EQUALS": NUMERIC_EQUALS,
        "NUMERIC_NOT_EQUALS": NUMERIC_NOT_EQUALS,
        "NUMERIC_LESS_THAN": NUMERIC_LESS_THAN,
        "NUMERIC_LESS_THAN_EQUALS": NUMERIC_LESS_THAN_EQUALS,
        "NUMERIC_GREATER_THAN": NUMERIC_GREATER_THAN,
        "NUMERIC_GREATER_THAN_EQUALS": NUMERIC_GREATER_THAN_EQUALS,
        "DATE_EQUALS": DATE_EQUALS,
        "DATE_NOT_EQUALS": DATE_NOT_EQUALS,
        "DATE_LESS_THAN": DATE_LESS_THAN,
        "DATE_LESS_THAN_EQUALS": DATE_LESS_THAN_EQUALS,
        "DATE_GREATER_THAN": DATE_GREATER_THAN,
        "DATE_GREATER_THAN_EQUALS": DATE_GREATER_THAN_EQUALS,
        "IP_ADDRESS": IP_ADDRESS,
        "NOT_IP_ADDRESS": NOT_IP_ADDRESS,
        "ARN_EQUALS": ARN_EQUALS,
        "ARN_NOT_EQUALS": ARN_NOT_EQUALS,
        "ARN_LIKE": ARN_LIKE,
        "ARN_NOT_LIKE": ARN_NOT_LIKE,
        "NULL": NULL,
    }

    # Add all service modules from resources package
    # Use __all__ instead of dir() since resources uses lazy loading
    import importlib

    for module_name in getattr(resources, "__all__", []):
        try:
            module = importlib.import_module(f"wetwire_aws.resources.{module_name}")
            namespace[module_name] = module
        except ImportError:
            pass  # Skip modules that fail to import

    return namespace


def setup_params(package_globals: dict[str, Any]) -> None:
    """Inject AWS types needed by params.py into the package namespace.

    Call this BEFORE `from .params import *` so that params.py can use
    `from . import *` to get access to Parameter, STRING, wetwire_aws, etc.

    This function injects:
    - wetwire_aws decorator
    - Parameter, Output, Mapping, TemplateCondition classes
    - All parameter type constants (STRING, NUMBER, KEY_PAIR, etc.)
    - Condition intrinsics (Equals, Not, And, Or, If, Condition)
    - Pseudo-parameters (AWS_REGION, AWS_ACCOUNT_ID, AWS_STACK_NAME)
    - PolicyStatement, DenyStatement, PolicyDocument classes

    Args:
        package_globals: The package's globals() dict

    Example:
        # In myapp/__init__.py
        from wetwire_aws.loader import setup_params, setup_resources

        setup_params(globals())

        from .params import *  # noqa: F403, F401

        setup_resources(__file__, __name__, globals())
    """
    # Import items needed by params.py
    from wetwire_aws.base import DenyStatement, PolicyDocument, PolicyStatement
    from wetwire_aws.decorator import wetwire_aws
    from wetwire_aws.intrinsics import ref
    from wetwire_aws.intrinsics.functions import (
        And,
        Equals,
        If,
        Not,
        Or,
    )
    from wetwire_aws.intrinsics.functions import Condition as ConditionIntrinsic
    from wetwire_aws.intrinsics.pseudo import (
        AWS_ACCOUNT_ID,
        AWS_NO_VALUE,
        AWS_REGION,
        AWS_STACK_NAME,
    )
    from wetwire_aws.params import (
        AMI_ID,
        AVAILABILITY_ZONE,
        COMMA_DELIMITED_LIST,
        HOSTED_ZONE_ID,
        INSTANCE_ID,
        KEY_PAIR,
        LIST_AVAILABILITY_ZONE,
        LIST_NUMBER,
        LIST_SECURITY_GROUP_ID,
        LIST_SUBNET_ID,
        NUMBER,
        SECURITY_GROUP_ID,
        SSM_PARAMETER_STRING,
        SSM_PARAMETER_STRING_LIST,
        STRING,
        SUBNET_ID,
        VOLUME_ID,
        VPC_ID,
    )
    from wetwire_aws.template import (
        Condition as TemplateCondition,
    )
    from wetwire_aws.template import (
        Mapping,
        Output,
        Parameter,
    )

    # Inject into package globals
    package_globals.update(
        {
            # Decorator
            "wetwire_aws": wetwire_aws,
            # Template components
            "Parameter": Parameter,
            "Output": Output,
            "Mapping": Mapping,
            "TemplateCondition": TemplateCondition,
            # Policy helpers
            "PolicyStatement": PolicyStatement,
            "DenyStatement": DenyStatement,
            "PolicyDocument": PolicyDocument,
            # Parameter type constants
            "STRING": STRING,
            "NUMBER": NUMBER,
            "LIST_NUMBER": LIST_NUMBER,
            "COMMA_DELIMITED_LIST": COMMA_DELIMITED_LIST,
            "SSM_PARAMETER_STRING": SSM_PARAMETER_STRING,
            "SSM_PARAMETER_STRING_LIST": SSM_PARAMETER_STRING_LIST,
            "AVAILABILITY_ZONE": AVAILABILITY_ZONE,
            "LIST_AVAILABILITY_ZONE": LIST_AVAILABILITY_ZONE,
            "AMI_ID": AMI_ID,
            "INSTANCE_ID": INSTANCE_ID,
            "KEY_PAIR": KEY_PAIR,
            "SECURITY_GROUP_ID": SECURITY_GROUP_ID,
            "LIST_SECURITY_GROUP_ID": LIST_SECURITY_GROUP_ID,
            "SUBNET_ID": SUBNET_ID,
            "LIST_SUBNET_ID": LIST_SUBNET_ID,
            "VPC_ID": VPC_ID,
            "VOLUME_ID": VOLUME_ID,
            "HOSTED_ZONE_ID": HOSTED_ZONE_ID,
            # Condition intrinsics
            "Equals": Equals,
            "Not": Not,
            "And": And,
            "Or": Or,
            "If": If,
            "Condition": ConditionIntrinsic,
            # Reference helper for parameter refs in conditions
            "ref": ref,
            # Pseudo-parameters
            "AWS_REGION": AWS_REGION,
            "AWS_ACCOUNT_ID": AWS_ACCOUNT_ID,
            "AWS_STACK_NAME": AWS_STACK_NAME,
            "AWS_NO_VALUE": AWS_NO_VALUE,
        }
    )


def setup_resources(
    init_file: str,
    package_name: str,
    package_globals: dict[str, Any],
    *,
    generate_stubs: bool = True,
) -> None:
    """Set up AWS CloudFormation resource imports with auto-decoration.

    Wrapper around dataclass_dsl.setup_resources with AWS-specific
    namespace injection and stub configuration pre-applied.

    Classes with a `resource:` annotation are auto-decorated.
    No need for explicit @wetwire_aws decorator.

    This function:
    1. Finds all .py files in the package directory
    2. Parses them to find class definitions and Ref[T]/Attr[T,...] references
    3. Builds a dependency graph from the references
    4. Imports modules in topological order
    5. Injects AWS decorators, types, and service modules into each module's namespace
    6. Auto-decorates classes with `resource:` annotation
    7. Generates .pyi stubs with AWS-specific imports for IDE support

    Args:
        init_file: Path to __init__.py (__file__)
        package_name: Package name (__name__)
        package_globals: Package globals dict (globals())
        generate_stubs: Whether to generate .pyi files (default: True)

    Example:
        # In myapp/resources/__init__.py
        from wetwire_aws.loader import setup_resources
        setup_resources(__file__, __name__, globals())

        # Resource files can use pure Python classes:
        # myapp/resources/storage.py
        from . import *

        class DataBucket:
            resource: s3.Bucket
            bucket_name = "data-lake"
    """
    # Import decorator here to avoid circular imports
    from wetwire_aws.decorator import wetwire_aws

    _setup_resources(
        init_file,
        package_name,
        package_globals,
        stub_config=AWS_STUB_CONFIG,
        generate_stubs=generate_stubs,
        extra_namespace=_get_aws_namespace(),
        auto_decorate=True,
        decorator=wetwire_aws,
    )
