"""
wetwire-aws: AWS CloudFormation synthesis for wetwire.

This package provides:
- @wetwire_aws decorator for defining CloudFormation resources
- CloudFormationTemplate for generating CF JSON/YAML
- CloudFormationProvider for serialization
- AWSContext for AWS-specific context values
- Intrinsic functions (ref, get_att, Sub, Join, etc.)
- Generated resource classes for all AWS services
"""

from wetwire_aws.base import CloudFormationResource, PropertyType
from wetwire_aws.context import AWSContext
from wetwire_aws.decorator import wetwire_aws
from wetwire_aws.provider import CloudFormationProvider
from wetwire_aws.intrinsics import (
    ARN,
    # Pseudo-parameters
    AWS_ACCOUNT_ID,
    AWS_NO_VALUE,
    AWS_NOTIFICATION_ARNS,
    AWS_PARTITION,
    AWS_REGION,
    AWS_STACK_ID,
    AWS_STACK_NAME,
    AWS_URL_SUFFIX,
    And,
    AttrType,
    Base64,
    ContextRef,
    Equals,
    GetAtt,
    GetAZs,
    If,
    ImportValue,
    Join,
    Not,
    Or,
    # Intrinsic functions
    Ref,
    RefDict,
    RefInfo,
    RefList,
    # graph-refs types for type annotations
    RefType,
    Select,
    Sub,
    get_att,
    get_dependencies,
    get_refs,
    ref,
)
from wetwire_aws.template import CloudFormationTemplate

__version__ = "0.1.0"

__all__ = [
    # Decorator
    "wetwire_aws",
    # Base classes
    "CloudFormationResource",
    "PropertyType",
    # Provider
    "CloudFormationProvider",
    # Context
    "AWSContext",
    # Template
    "CloudFormationTemplate",
    # Reference helpers
    "ref",
    "get_att",
    # Attribute constants
    "ARN",
    # graph-refs types for type annotations
    "RefType",
    "AttrType",
    "RefList",
    "RefDict",
    "ContextRef",
    "RefInfo",
    "get_refs",
    "get_dependencies",
    # Intrinsic functions
    "Ref",
    "GetAtt",
    "Sub",
    "Join",
    "Select",
    "If",
    "Equals",
    "And",
    "Or",
    "Not",
    "Base64",
    "GetAZs",
    "ImportValue",
    # Pseudo-parameters
    "AWS_ACCOUNT_ID",
    "AWS_NOTIFICATION_ARNS",
    "AWS_NO_VALUE",
    "AWS_PARTITION",
    "AWS_REGION",
    "AWS_STACK_ID",
    "AWS_STACK_NAME",
    "AWS_URL_SUFFIX",
]
