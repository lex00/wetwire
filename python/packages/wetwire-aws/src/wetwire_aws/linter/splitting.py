"""File splitting utilities for wetwire-aws packages.

This module provides utilities for splitting large resource files into
smaller, category-based files. The linter's FileTooLarge rule (WAW010)
uses these utilities to suggest file splits, and the importer uses them
to generate appropriately-sized files.

Categories:
    storage: S3, EFS, FSx
    compute: EC2 (instances), Lambda, ECS, EKS, Batch
    database: RDS, DynamoDB, ElastiCache, etc.
    network: VPC, Subnet, Load Balancers, Route53, etc.
    security: IAM, Cognito, KMS, SecretsManager, etc.
    messaging: SNS, SQS, EventBridge, StepFunctions
    monitoring: CloudWatch, Logs, CloudTrail
    cicd: CodeBuild, CodePipeline, CodeCommit, etc.
    infra: CloudFormation, Config, ServiceCatalog
    main: Everything else or tightly-coupled resources
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "SERVICE_CATEGORIES",
    "EC2_NETWORK_TYPES",
    "MAX_RESOURCES_PER_FILE",
    "categorize_resource_type",
    "is_ec2_network_type",
    "suggest_file_splits",
    "calculate_scc_weight",
    "ResourceInfo",
]

# Default maximum number of resources per file
MAX_RESOURCES_PER_FILE = 15

# =============================================================================
# Service Category Mapping
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
# NOTE: This set is kept for backward compatibility but the dynamic inference
# function is_ec2_network_type() is preferred and covers more types.
EC2_NETWORK_TYPES: set[str] = {
    "VPC",
    "Subnet",
    "InternetGateway",
    "NatGateway",
    "RouteTable",
    "Route",
    "SecurityGroup",
    "SecurityGroupIngress",
    "SecurityGroupEgress",
    "NetworkAcl",
    "NetworkAclEntry",
    "VPCEndpoint",
    "EIP",
    "EIPAssociation",
    "VPCGatewayAttachment",
    "SubnetRouteTableAssociation",
    "SubnetNetworkAclAssociation",
    "NetworkInterface",
    "NetworkInterfaceAttachment",
    "TransitGateway",
    "TransitGatewayAttachment",
    "VPCPeeringConnection",
    "VPNGateway",
    "VPNConnection",
    "CustomerGateway",
}


def is_ec2_network_type(type_name: str) -> bool:
    """Infer if an EC2 type is network-related based on naming patterns.

    This function uses keyword-based heuristics to determine whether an EC2
    resource type belongs in network.py rather than compute.py. This dynamic
    approach handles new resource types without requiring manual updates to
    a static list.

    Args:
        type_name: The EC2 resource type name (e.g., "VPC", "Instance",
            "SecurityGroupIngress")

    Returns:
        True if the type should be categorized as network, False for compute.

    Examples:
        >>> is_ec2_network_type("VPC")
        True
        >>> is_ec2_network_type("SecurityGroupIngress")
        True
        >>> is_ec2_network_type("Instance")
        False
        >>> is_ec2_network_type("LaunchTemplate")
        False
    """
    # Special case: Endpoint types are always network
    if "Endpoint" in type_name:
        return True

    # Exclude compute keywords first (these take precedence)
    compute_keywords = [
        "Instance",
        "Fleet",
        "Host",
        "KeyPair",
        "Capacity",
        "Volume",
        "Placement",
        "IPAM",  # IP Address Management is infrastructure, not networking
        "Snapshot",
        "Enclave",
        "LaunchTemplate",
        "SpotFleet",
        "Image",
        "AMI",
    ]
    if any(kw in type_name for kw in compute_keywords):
        return False

    # Include network keywords
    network_keywords = [
        "VPC",
        "Subnet",
        "Route",
        "Gateway",
        "Network",
        "Interface",
        "Security",
        "Acl",
        "VPN",
        "Transit",
        "Peering",
        "EIP",
        "Customer",
        "DHCP",
        "Carrier",
        "Insights",
        "FlowLog",
        "Association",
        "Attachment",
        "Prefix",  # PrefixList
        "Traffic",  # TrafficMirror*
        "Egress",  # EgressOnlyInternetGateway
        "Ingress",
        "LocalGateway",
        "Verified",  # VerifiedAccess*
    ]
    return any(kw in type_name for kw in network_keywords)


def categorize_resource_type(resource_type: str) -> str:
    """Get the category for a CloudFormation resource type.

    Maps AWS resource types to category names for file organization.
    Special handling for EC2 VPC/networking resources.

    Args:
        resource_type: CloudFormation resource type (e.g., "AWS::S3::Bucket")

    Returns:
        Category name (e.g., "storage", "network", "compute", "main")

    Examples:
        >>> categorize_resource_type("AWS::S3::Bucket")
        'storage'
        >>> categorize_resource_type("AWS::EC2::Instance")
        'compute'
        >>> categorize_resource_type("AWS::EC2::VPC")
        'network'
    """
    # Parse resource type: "AWS::EC2::VPC" → service="EC2", type_name="VPC"
    parts = resource_type.split("::")
    if len(parts) != 3 or parts[0] != "AWS":
        return "main"

    service = parts[1]
    type_name = parts[2]

    # Special case: EC2 VPC/networking resources go to network, not compute
    # Use dynamic inference to handle new resource types automatically
    if service == "EC2" and is_ec2_network_type(type_name):
        return "network"

    return SERVICE_CATEGORIES.get(service, "main")


@dataclass
class ResourceInfo:
    """Information about a resource for file splitting.

    Attributes:
        name: Class name of the resource (e.g., "MyBucket")
        resource_type: CloudFormation resource type (e.g., "AWS::S3::Bucket")
        dependencies: Set of class names this resource depends on
    """

    name: str
    resource_type: str
    dependencies: set[str]


def suggest_file_splits(
    resources: list[ResourceInfo],
    max_per_file: int = MAX_RESOURCES_PER_FILE,
    sccs: list[list[str]] | None = None,
) -> dict[str, list[str]]:
    """Suggest how to split resources into category-based files.

    This function implements the file splitting algorithm:
    1. If SCCs provided, put the most tightly-coupled in main.py (up to max)
    2. Categorize remaining resources by AWS service
    3. If a category has > max_per_file, split into numbered files

    Args:
        resources: List of ResourceInfo objects to split
        max_per_file: Maximum resources per file (default 15)
        sccs: Optional list of strongly connected components (class name lists)
              Used to determine which resources go in main.py

    Returns:
        Dict mapping filename (without .py) to list of class names
        E.g., {"main": ["VPC", "Subnet"], "storage": ["Bucket"], "storage2": [...]}

    Examples:
        >>> resources = [
        ...     ResourceInfo("MyBucket", "AWS::S3::Bucket", set()),
        ...     ResourceInfo("MyVPC", "AWS::EC2::VPC", set()),
        ... ]
        >>> splits = suggest_file_splits(resources)
        >>> splits
        {'storage': ['MyBucket'], 'network': ['MyVPC']}
    """
    # Build lookup for resources by name
    resource_by_name: dict[str, ResourceInfo] = {r.name: r for r in resources}

    # Track which resources are assigned
    assigned: set[str] = set()
    result: dict[str, list[str]] = {}

    # Step 1: If SCCs provided, calculate weights and assign heaviest to main.py
    if sccs:
        # Calculate weight for each SCC
        weighted_sccs = []
        for scc in sccs:
            if len(scc) > 1:  # Only consider non-trivial SCCs
                weight = calculate_scc_weight(scc, resource_by_name)
                weighted_sccs.append((weight, scc))

        # Sort by weight descending
        weighted_sccs.sort(key=lambda x: -x[0])

        # Add heaviest SCCs to main.py until we hit the limit
        main_resources: list[str] = []
        for _weight, scc in weighted_sccs:
            if len(main_resources) + len(scc) <= max_per_file:
                main_resources.extend(scc)
                assigned.update(scc)
            else:
                break

        if main_resources:
            result["main"] = main_resources

    # Step 2: Categorize remaining resources
    categories: dict[str, list[str]] = {}
    for resource in resources:
        if resource.name in assigned:
            continue

        category = categorize_resource_type(resource.resource_type)
        if category not in categories:
            categories[category] = []
        categories[category].append(resource.name)

    # Step 3: Split categories if > max_per_file
    for category, names in categories.items():
        if len(names) <= max_per_file:
            # Fits in one file
            if category in result:
                # main.py already exists, merge if room
                if len(result[category]) + len(names) <= max_per_file:
                    result[category].extend(names)
                else:
                    result[f"{category}1"] = names
            else:
                result[category] = names
        else:
            # Need to split into multiple files
            chunks = _split_into_chunks(names, max_per_file)
            for i, chunk in enumerate(chunks, start=1):
                result[f"{category}{i}"] = chunk

    return result


def _split_into_chunks(items: list[str], chunk_size: int) -> list[list[str]]:
    """Split a list into chunks of at most chunk_size."""
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def calculate_scc_weight(
    scc: list[str], resource_by_name: dict[str, ResourceInfo]
) -> int:
    """Calculate the "connectivity weight" of a strongly connected component.

    Higher weight = more tightly coupled internally, better candidate for main.py.
    Weight is the number of internal dependency edges within the SCC.

    Args:
        scc: List of class names in the SCC
        resource_by_name: Lookup dict from class name to ResourceInfo

    Returns:
        Number of internal edges (dependencies within the SCC)

    Examples:
        >>> resources = {
        ...     "A": ResourceInfo("A", "AWS::S3::Bucket", {"B", "C"}),
        ...     "B": ResourceInfo("B", "AWS::S3::Bucket", {"A"}),
        ...     "C": ResourceInfo("C", "AWS::S3::Bucket", set()),
        ... }
        >>> calculate_scc_weight(["A", "B"], resources)
        2  # A->B and B->A
    """
    scc_set = set(scc)
    weight = 0

    for name in scc:
        resource = resource_by_name.get(name)
        if resource:
            # Count dependencies that are also in the SCC
            internal_deps = resource.dependencies & scc_set
            weight += len(internal_deps)

    return weight
