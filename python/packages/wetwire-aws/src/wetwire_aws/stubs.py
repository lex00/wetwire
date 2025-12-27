"""
AWS-specific stub configuration for graph_refs_dataclasses.

Provides AWS_STUB_CONFIG for generating .pyi stub files that work
with wetwire-aws imports.
"""

from graph_refs_dataclasses import StubConfig

# All names exported from wetwire_aws
AWS_CORE_EXPORTS = [
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
    # Loader
    "setup_resources",
]

AWS_STUB_CONFIG = StubConfig(
    package_name="wetwire_aws",
    core_imports=AWS_CORE_EXPORTS,
    expand_star_imports={
        "wetwire_aws": AWS_CORE_EXPORTS,
    },
)
