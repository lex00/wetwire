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

# PYTHON_KEYWORDS moved to wetwire.codegen.transforms
