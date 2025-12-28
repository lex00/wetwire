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
from wetwire_aws.template import (
    Condition as TemplateCondition,
    Mapping,
    Output,
    Parameter,
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

# Re-export TemplateCondition for backward compatibility
# NOTE: The intrinsic Condition is exported separately for use in condition expressions
from wetwire_aws.intrinsics import (
    Condition,  # Intrinsic function for referencing conditions by name
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
    Cidr,
    ContextRef,
    Equals,
    FindInMap,
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
    # dataclass-dsl types for type annotations
    RefType,
    Select,
    Split,
    Sub,
    Transform,
    get_att,
    get_dependencies,
    get_refs,
    ref,
)
# Condition is already imported above from intrinsics
ConditionIntrinsic = Condition  # Alias for backward compatibility
from wetwire_aws.loader import setup_resources
from wetwire_aws.provider import CloudFormationProvider
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
    # Template components (for importer)
    "Parameter",
    "Output",
    "Mapping",
    "Condition",
    "TemplateCondition",
    # Parameter type constants
    "STRING",
    "NUMBER",
    "LIST_NUMBER",
    "COMMA_DELIMITED_LIST",
    "SSM_PARAMETER_STRING",
    "SSM_PARAMETER_STRING_LIST",
    "AVAILABILITY_ZONE",
    "LIST_AVAILABILITY_ZONE",
    "AMI_ID",
    "INSTANCE_ID",
    "KEY_PAIR",
    "SECURITY_GROUP_ID",
    "LIST_SECURITY_GROUP_ID",
    "SUBNET_ID",
    "LIST_SUBNET_ID",
    "VPC_ID",
    "VOLUME_ID",
    "HOSTED_ZONE_ID",
    # Reference helpers
    "ref",
    "get_att",
    # Attribute constants
    "ARN",
    # dataclass-dsl types for type annotations
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
    "Split",
    "If",
    "Equals",
    "And",
    "Or",
    "Not",
    "Base64",
    "GetAZs",
    "ImportValue",
    "FindInMap",
    "Transform",
    "Cidr",
    "ConditionIntrinsic",
    # Pseudo-parameters
    "AWS_ACCOUNT_ID",
    "AWS_NOTIFICATION_ARNS",
    "AWS_NO_VALUE",
    "AWS_PARTITION",
    "AWS_REGION",
    "AWS_STACK_ID",
    "AWS_STACK_NAME",
    "AWS_URL_SUFFIX",
    # Resource loader
    "setup_resources",
]
