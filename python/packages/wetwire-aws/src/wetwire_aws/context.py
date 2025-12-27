"""
AWS-specific context for CloudFormation deployments.

Extends the core Context with AWS pseudo-parameters that can be
resolved at runtime or used in CloudFormation templates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from graph_refs import ContextRef
from wetwire import Context

from wetwire_aws.intrinsics.functions import Ref


@dataclass
class AWSContext(Context):
    """
    AWS-specific context with CloudFormation pseudo-parameters.

    Pseudo-parameters are special values that CloudFormation resolves
    at stack creation/update time. This context allows you to:
    1. Use real values in local testing
    2. Generate pseudo-parameter references in templates

    Example:
        >>> ctx = AWSContext(
        ...     project="myapp",
        ...     environment="production",
        ...     region="us-west-2",
        ...     account_id="123456789012",
        ... )
        >>> ctx.region
        'us-west-2'

    For CloudFormation templates, use the pseudo-parameter intrinsics:
        >>> from wetwire_aws import AWS_REGION, AWS_ACCOUNT_ID
        >>> # These serialize to {"Ref": "AWS::Region"}, etc.
    """

    # AWS pseudo-parameters (None means use CF pseudo-parameter at runtime)
    region: str | None = None
    account_id: str | None = None
    stack_name: str | None = None
    stack_id: str | None = None
    partition: str | None = None
    url_suffix: str | None = None

    def resolve_pseudo_parameter(self, name: str) -> Any:
        """
        Resolve an AWS pseudo-parameter.

        If a concrete value is set, returns it. Otherwise, returns
        a CloudFormation Ref intrinsic for runtime resolution.

        Args:
            name: The pseudo-parameter name (e.g., "AWS::Region")

        Returns:
            The concrete value or a Ref intrinsic
        """
        mapping = {
            "AWS::Region": self.region,
            "AWS::AccountId": self.account_id,
            "AWS::StackName": self.stack_name,
            "AWS::StackId": self.stack_id,
            "AWS::Partition": self.partition,
            "AWS::URLSuffix": self.url_suffix,
        }

        value = mapping.get(name)
        if value is not None:
            return value
        # Return a Ref intrinsic for CloudFormation to resolve
        return Ref(name)

    def resolve(self, context_ref: ContextRef[str]) -> Any:  # type: ignore[type-arg]
        """
        Resolve a ContextRef to its value.

        Handles both standard context values (project, environment)
        and AWS pseudo-parameters.

        Args:
            context_ref: The context reference to resolve

        Returns:
            The resolved value or Ref intrinsic
        """
        args = getattr(context_ref, "__args__", ())
        if args:
            name = args[0]
            if isinstance(name, str):
                # Check if it's an AWS pseudo-parameter
                if name.startswith("AWS::"):
                    return self.resolve_pseudo_parameter(name)
                # Otherwise use standard context resolution
                return self.get(name)
        return None


# Pre-built context references for AWS pseudo-parameters
AWS_REGION: ContextRef[str] = ContextRef["AWS::Region"]  # type: ignore[assignment,type-arg]
AWS_ACCOUNT_ID: ContextRef[str] = ContextRef["AWS::AccountId"]  # type: ignore[assignment,type-arg]
AWS_STACK_NAME: ContextRef[str] = ContextRef["AWS::StackName"]  # type: ignore[assignment,type-arg]
AWS_STACK_ID: ContextRef[str] = ContextRef["AWS::StackId"]  # type: ignore[assignment,type-arg]
AWS_PARTITION: ContextRef[str] = ContextRef["AWS::Partition"]  # type: ignore[assignment,type-arg]
AWS_URL_SUFFIX: ContextRef[str] = ContextRef["AWS::URLSuffix"]  # type: ignore[assignment,type-arg]
