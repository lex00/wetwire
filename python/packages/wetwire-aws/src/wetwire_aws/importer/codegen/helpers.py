"""Helper utilities and constants for code generation.

This module provides utility functions and mappings used throughout
the code generation process.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from wetwire_aws.naming import sanitize_class_name, to_pascal_case, to_snake_case

if TYPE_CHECKING:
    from wetwire_aws.importer.ir import IRResource

# Re-export for convenience
__all__ = [
    "sanitize_class_name",
    "to_pascal_case",
    "to_snake_case",
    "get_resource_category",
    "resolve_resource_type",
    "SERVICE_CATEGORIES",
]


# =============================================================================
# Service Category Mapping for Resource File Organization
# =============================================================================

SERVICE_CATEGORIES: dict[str, str] = {
    # Compute
    "EC2": "compute",
    "Lambda": "compute",
    "ECS": "compute",
    "EKS": "compute",
    "Batch": "compute",
    "AutoScaling": "compute",
    # Storage
    "S3": "storage",
    "EFS": "storage",
    "FSx": "storage",
    # Database
    "RDS": "database",
    "DynamoDB": "database",
    "ElastiCache": "database",
    "Neptune": "database",
    "DocumentDB": "database",
    "Redshift": "database",
    # Networking
    "ElasticLoadBalancing": "network",
    "ElasticLoadBalancingV2": "network",
    "Route53": "network",
    "CloudFront": "network",
    "APIGateway": "network",
    "ApiGatewayV2": "network",
    # Security/IAM
    "IAM": "security",
    "Cognito": "security",
    "SecretsManager": "security",
    "KMS": "security",
    "WAF": "security",
    "WAFv2": "security",
    "ACM": "security",
    "SSM": "security",
    # Messaging/Integration
    "SNS": "messaging",
    "SQS": "messaging",
    "EventBridge": "messaging",
    "Events": "messaging",
    "StepFunctions": "messaging",
    # Monitoring/Logging
    "CloudWatch": "monitoring",
    "Logs": "monitoring",
    "CloudTrail": "monitoring",
    # CI/CD
    "CodeBuild": "cicd",
    "CodePipeline": "cicd",
    "CodeCommit": "cicd",
    "CodeDeploy": "cicd",
    # Infrastructure
    "CloudFormation": "infra",
    "Config": "infra",
    "ServiceCatalog": "infra",
}

# EC2 resource types that should go to network.py instead of compute.py
EC2_NETWORK_TYPES: set[str] = {
    "VPC",
    "Subnet",
    "InternetGateway",
    "NatGateway",
    "RouteTable",
    "Route",
    "SecurityGroup",
    "NetworkAcl",
    "VPCEndpoint",
    "EIP",
    "VPCGatewayAttachment",
    "SubnetRouteTableAssociation",
    "NetworkInterface",
}


def get_resource_category(resource: "IRResource") -> str:
    """Get the category file for a resource based on its AWS service.

    Currently returns 'main' for all resources to avoid cross-file cycles.
    The topological loader handles dependencies within a single file correctly,
    but cross-file cycles require more sophisticated handling.

    TODO: Re-enable categorization once the loader can handle cross-file cycles.
    """
    # Always put resources in main.py to avoid cross-file dependency cycles
    return "main"


# =============================================================================
# Resource Type Resolution
# =============================================================================

# Map CloudFormation service names to wetwire_aws module names
SERVICE_TO_MODULE: dict[str, str] = {
    # Handle special cases where CF service name differs from module name
    "Lambda": "lambda_",  # lambda is a Python keyword
    "ElasticLoadBalancing": "elasticloadbalancing",
    "ElasticLoadBalancingV2": "elasticloadbalancingv2",
    "StepFunctions": "stepfunctions",
    "CloudFormation": "cloudformation",
    "CloudWatch": "cloudwatch",
    "CloudFront": "cloudfront",
    "CloudTrail": "cloudtrail",
    "SecretsManager": "secretsmanager",
    "EventBridge": "events",  # EventBridge uses events module
    "ApiGatewayV2": "apigatewayv2",
    "APIGateway": "apigateway",
    "CodeBuild": "codebuild",
    "CodePipeline": "codepipeline",
    "CodeCommit": "codecommit",
    "CodeDeploy": "codedeploy",
    "ServiceCatalog": "servicecatalog",
    # Most services use lowercase version of CF name
}


def resolve_resource_type(cf_type: str) -> tuple[str, str] | None:
    """Resolve a CloudFormation resource type to (module, class) tuple.

    Args:
        cf_type: CloudFormation resource type (e.g., "AWS::S3::Bucket")

    Returns:
        Tuple of (module_name, class_name) or None if not recognized.

    Example:
        >>> resolve_resource_type("AWS::S3::Bucket")
        ('s3', 'Bucket')
        >>> resolve_resource_type("AWS::Lambda::Function")
        ('lambda_', 'Function')
    """
    if not cf_type.startswith("AWS::"):
        return None

    parts = cf_type.split("::")
    if len(parts) != 3:
        return None

    _, service, type_name = parts

    # Get module name (handle special cases)
    module = SERVICE_TO_MODULE.get(service, service.lower())

    # Check if the module and class actually exist in wetwire_aws.resources
    if not _resource_class_exists(module, type_name):
        return None

    return (module, type_name)


# Cache for known resource classes: {(module, class_name): exists}
_KNOWN_RESOURCE_CLASSES: dict[tuple[str, str], bool] | None = None


def _resource_class_exists(module_name: str, class_name: str) -> bool:
    """Check if a resource class exists in wetwire_aws.resources.

    Args:
        module_name: The module name (e.g., 's3', 'lambda_')
        class_name: The class name (e.g., 'Bucket', 'Function')

    Returns:
        True if the class exists in the module, False otherwise.
    """
    global _KNOWN_RESOURCE_CLASSES

    if _KNOWN_RESOURCE_CLASSES is None:
        # Build cache by scanning module files for class definitions
        import re
        from pathlib import Path

        _KNOWN_RESOURCE_CLASSES = {}
        try:
            import wetwire_aws.resources as resources_pkg

            resources_dir = Path(resources_pkg.__file__).parent

            for entry in resources_dir.iterdir():
                if entry.name.startswith("_"):
                    continue

                mod_name = None
                init_file = None

                if entry.is_dir() and (entry / "__init__.py").exists():
                    mod_name = entry.name
                    init_file = entry / "__init__.py"
                elif entry.is_file() and entry.suffix == ".py":
                    mod_name = entry.stem
                    init_file = entry

                if mod_name and init_file and init_file.exists():
                    try:
                        content = init_file.read_text()
                        # Find all class definitions
                        for match in re.finditer(r"^class\s+(\w+)", content, re.MULTILINE):
                            _KNOWN_RESOURCE_CLASSES[(mod_name, match.group(1))] = True
                    except Exception:
                        pass

        except (ImportError, AttributeError):
            pass

    return _KNOWN_RESOURCE_CLASSES.get((module_name, class_name), False)


# =============================================================================
# Parameter Type Mapping
# =============================================================================

# Map CloudFormation parameter types to wetwire_aws constants
PARAMETER_TYPE_MAP: dict[str, str] = {
    "String": "STRING",
    "Number": "NUMBER",
    "List<Number>": "LIST_NUMBER",
    "CommaDelimitedList": "COMMA_DELIMITED_LIST",
    "AWS::SSM::Parameter::Value<String>": "SSM_PARAMETER_STRING",
    "AWS::SSM::Parameter::Value<List<String>>": "SSM_PARAMETER_STRING_LIST",
    "AWS::EC2::AvailabilityZone::Name": "AVAILABILITY_ZONE",
    "List<AWS::EC2::AvailabilityZone::Name>": "LIST_AVAILABILITY_ZONE",
    "AWS::EC2::Image::Id": "AMI_ID",
    "AWS::EC2::Instance::Id": "INSTANCE_ID",
    "AWS::EC2::KeyPair::KeyName": "KEY_PAIR",
    "AWS::EC2::SecurityGroup::Id": "SECURITY_GROUP_ID",
    "List<AWS::EC2::SecurityGroup::Id>": "LIST_SECURITY_GROUP_ID",
    "AWS::EC2::Subnet::Id": "SUBNET_ID",
    "List<AWS::EC2::Subnet::Id>": "LIST_SUBNET_ID",
    "AWS::EC2::VPC::Id": "VPC_ID",
    "AWS::EC2::Volume::Id": "VOLUME_ID",
    "AWS::Route53::HostedZone::Id": "HOSTED_ZONE_ID",
}

# =============================================================================
# Pseudo-Parameter Mapping
# =============================================================================

# Map CloudFormation pseudo-parameters to wetwire_aws constants
PSEUDO_PARAMETER_MAP: dict[str, str] = {
    "AWS::AccountId": "AWS_ACCOUNT_ID",
    "AWS::NotificationARNs": "AWS_NOTIFICATION_ARNS",
    "AWS::NoValue": "AWS_NO_VALUE",
    "AWS::Partition": "AWS_PARTITION",
    "AWS::Region": "AWS_REGION",
    "AWS::StackId": "AWS_STACK_ID",
    "AWS::StackName": "AWS_STACK_NAME",
    "AWS::URLSuffix": "AWS_URL_SUFFIX",
}
