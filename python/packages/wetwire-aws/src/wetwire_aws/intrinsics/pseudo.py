"""
CloudFormation pseudo-parameters.

These are special parameters that AWS CloudFormation provides automatically.
They resolve to values at deployment time.

See: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/pseudo-parameter-reference.html
"""

from wetwire_aws.intrinsics.functions import Ref

# Pseudo-parameters as Ref objects
AWS_ACCOUNT_ID = Ref("AWS::AccountId")
"""The AWS account ID of the account in which the stack is being created."""

AWS_NOTIFICATION_ARNS = Ref("AWS::NotificationARNs")
"""List of notification ARNs for the current stack."""

AWS_NO_VALUE = Ref("AWS::NoValue")
"""Removes the resource property when specified as return value in Fn::If."""

AWS_PARTITION = Ref("AWS::Partition")
"""The partition in which the resource is located (aws, aws-cn, aws-us-gov)."""

AWS_REGION = Ref("AWS::Region")
"""The AWS Region in which the resource is being created."""

AWS_STACK_ID = Ref("AWS::StackId")
"""The ID of the stack."""

AWS_STACK_NAME = Ref("AWS::StackName")
"""The name of the stack."""

AWS_URL_SUFFIX = Ref("AWS::URLSuffix")
"""The suffix for a domain (amazonaws.com, amazonaws.com.cn)."""
