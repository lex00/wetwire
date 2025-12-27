"""
Code generation configuration.

Contains source URLs, version information, and settings for the
codegen pipeline.
"""

from pathlib import Path

# Generator version - bump when codegen logic changes
GENERATOR_VERSION = "1.0.0"

# CloudFormation spec URL
CF_SPEC_URL = "https://d1uauaxba7bl26.cloudfront.net/latest/gzip/CloudFormationResourceSpecification.json"

# Paths
PACKAGE_ROOT = Path(__file__).parent.parent
SPECS_DIR = PACKAGE_ROOT / "specs"
RESOURCES_DIR = PACKAGE_ROOT / "src" / "wetwire_aws" / "resources"

# Source definitions for fetch stage
SOURCES = [
    {
        "name": "cloudformation-spec",
        "type": "http",
        "url": CF_SPEC_URL,
        "filename": "CloudFormationResourceSpecification.json",
        "extract_version": lambda data: data.get("ResourceSpecificationVersion"),
    },
    {
        "name": "botocore",
        "type": "pip",
        "package": "botocore",
    },
]

# Services to prioritize (generate first for testing)
PRIORITY_SERVICES = [
    "s3",
    "ec2",
    "iam",
    "lambda",
    "dynamodb",
    "sqs",
    "sns",
    "rds",
    "cloudwatch",
    "apigateway",
]

# Reserved Python keywords and builtins that need renaming
PYTHON_KEYWORDS = {
    # Python keywords
    "and": "and_",
    "as": "as_",
    "assert": "assert_",
    "async": "async_",
    "await": "await_",
    "break": "break_",
    "class": "class_",
    "continue": "continue_",
    "def": "def_",
    "del": "del_",
    "elif": "elif_",
    "else": "else_",
    "except": "except_",
    "finally": "finally_",
    "for": "for_",
    "from": "from_",
    "global": "global_",
    "if": "if_",
    "import": "import_",
    "in": "in_",
    "is": "is_",
    "lambda": "lambda_",
    "None": "none_",
    "nonlocal": "nonlocal_",
    "not": "not_",
    "or": "or_",
    "pass": "pass_",
    "raise": "raise_",
    "return": "return_",
    "True": "true_",
    "False": "false_",
    "try": "try_",
    "type": "type_",
    "while": "while_",
    "with": "with_",
    "yield": "yield_",
    # Names that shadow our imports
    "field": "field_",
    "dataclass": "dataclass_",
}
