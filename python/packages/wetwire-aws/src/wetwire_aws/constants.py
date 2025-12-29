"""IAM policy condition operator constants.

These constants are used as dictionary keys in policy conditions
instead of string literals, providing better IDE support and
reducing typos.

Example:
    condition = {
        BOOL: {"aws:SecureTransport": False},
        STRING_EQUALS: {"s3:x-amz-acl": "bucket-owner-full-control"},
    }
"""

# String condition operators
STRING_EQUALS = "StringEquals"
STRING_NOT_EQUALS = "StringNotEquals"
STRING_EQUALS_IGNORE_CASE = "StringEqualsIgnoreCase"
STRING_NOT_EQUALS_IGNORE_CASE = "StringNotEqualsIgnoreCase"
STRING_LIKE = "StringLike"
STRING_NOT_LIKE = "StringNotLike"

# Numeric condition operators
NUMERIC_EQUALS = "NumericEquals"
NUMERIC_NOT_EQUALS = "NumericNotEquals"
NUMERIC_LESS_THAN = "NumericLessThan"
NUMERIC_LESS_THAN_EQUALS = "NumericLessThanEquals"
NUMERIC_GREATER_THAN = "NumericGreaterThan"
NUMERIC_GREATER_THAN_EQUALS = "NumericGreaterThanEquals"

# Date condition operators
DATE_EQUALS = "DateEquals"
DATE_NOT_EQUALS = "DateNotEquals"
DATE_LESS_THAN = "DateLessThan"
DATE_LESS_THAN_EQUALS = "DateLessThanEquals"
DATE_GREATER_THAN = "DateGreaterThan"
DATE_GREATER_THAN_EQUALS = "DateGreaterThanEquals"

# Boolean condition operator
BOOL = "Bool"

# IP address condition operators
IP_ADDRESS = "IpAddress"
NOT_IP_ADDRESS = "NotIpAddress"

# ARN condition operators
ARN_EQUALS = "ArnEquals"
ARN_NOT_EQUALS = "ArnNotEquals"
ARN_LIKE = "ArnLike"
ARN_NOT_LIKE = "ArnNotLike"

# Null check operator
NULL = "Null"

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


__all__ = [
    # String operators
    "STRING_EQUALS",
    "STRING_NOT_EQUALS",
    "STRING_EQUALS_IGNORE_CASE",
    "STRING_NOT_EQUALS_IGNORE_CASE",
    "STRING_LIKE",
    "STRING_NOT_LIKE",
    # Numeric operators
    "NUMERIC_EQUALS",
    "NUMERIC_NOT_EQUALS",
    "NUMERIC_LESS_THAN",
    "NUMERIC_LESS_THAN_EQUALS",
    "NUMERIC_GREATER_THAN",
    "NUMERIC_GREATER_THAN_EQUALS",
    # Date operators
    "DATE_EQUALS",
    "DATE_NOT_EQUALS",
    "DATE_LESS_THAN",
    "DATE_LESS_THAN_EQUALS",
    "DATE_GREATER_THAN",
    "DATE_GREATER_THAN_EQUALS",
    # Boolean operator
    "BOOL",
    # IP address operators
    "IP_ADDRESS",
    "NOT_IP_ADDRESS",
    # ARN operators
    "ARN_EQUALS",
    "ARN_NOT_EQUALS",
    "ARN_LIKE",
    "ARN_NOT_LIKE",
    # Null check
    "NULL",
    # Parameter mappings
    "PARAMETER_TYPE_MAP",
    "PSEUDO_PARAMETER_MAP",
]
