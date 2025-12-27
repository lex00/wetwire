"""
CloudFormation intrinsic functions and pseudo-parameters.

This module provides Python representations of CloudFormation intrinsic
functions that are serialized to their JSON equivalents during template
generation.
"""

from wetwire_aws.intrinsics.functions import (
    And,
    Base64,
    Cidr,
    Condition,
    Equals,
    FindInMap,
    GetAtt,
    GetAZs,
    If,
    ImportValue,
    Join,
    Not,
    Or,
    Ref,
    Select,
    Split,
    Sub,
    Transform,
)
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
from wetwire_aws.intrinsics.refs import (
    ARN,
    ContextRef,
    RefDict,
    RefInfo,
    RefList,
    get_att,
    get_dependencies,
    get_refs,
    ref,
)
from wetwire_aws.intrinsics.refs import (
    Attr as AttrType,
)
from wetwire_aws.intrinsics.refs import (
    # Re-export graph-refs types for type annotations
    Ref as RefType,
)

__all__ = [
    # Reference helpers (wetwire pattern)
    "ref",
    "get_att",
    # Common attribute constants
    "ARN",
    # graph-refs type annotations
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
    "Condition",
    "FindInMap",
    "Split",
    "Transform",
    "Cidr",
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
