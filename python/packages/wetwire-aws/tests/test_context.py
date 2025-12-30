"""Tests for AWSContext."""

from wetwire_aws import AWSContext
from wetwire_aws.intrinsics.functions import Ref


class TestAWSContext:
    """Test AWSContext for pseudo-parameters."""

    def test_context_with_concrete_values(self):
        """Test that concrete values are returned when set."""
        ctx = AWSContext(
            project="myapp",
            environment="production",
            region="us-west-2",
            account_id="123456789012",
        )

        assert ctx.project == "myapp"
        assert ctx.environment == "production"
        assert ctx.region == "us-west-2"
        assert ctx.account_id == "123456789012"

    def test_context_defaults_to_none(self):
        """Test that pseudo-parameters default to None."""
        ctx = AWSContext()

        assert ctx.region is None
        assert ctx.account_id is None
        assert ctx.stack_name is None

    def test_resolve_pseudo_parameter_with_value(self):
        """Test resolving a pseudo-parameter when a value is set."""
        ctx = AWSContext(region="us-east-1")

        result = ctx.resolve_pseudo_parameter("AWS::Region")
        assert result == "us-east-1"

    def test_resolve_pseudo_parameter_without_value(self):
        """Test resolving a pseudo-parameter when no value is set."""
        ctx = AWSContext()

        result = ctx.resolve_pseudo_parameter("AWS::Region")
        assert isinstance(result, Ref)
        assert result.to_dict() == {"Ref": "AWS::Region"}

    def test_resolve_all_pseudo_parameters(self):
        """Test resolving all pseudo-parameters."""
        ctx = AWSContext(
            region="us-west-2",
            account_id="123456789012",
            stack_name="my-stack",
            stack_id="arn:aws:cloudformation:...",
            partition="aws",
            url_suffix="amazonaws.com",
        )

        assert ctx.resolve_pseudo_parameter("AWS::Region") == "us-west-2"
        assert ctx.resolve_pseudo_parameter("AWS::AccountId") == "123456789012"
        assert ctx.resolve_pseudo_parameter("AWS::StackName") == "my-stack"
        assert (
            ctx.resolve_pseudo_parameter("AWS::StackId") == "arn:aws:cloudformation:..."
        )
        assert ctx.resolve_pseudo_parameter("AWS::Partition") == "aws"
        assert ctx.resolve_pseudo_parameter("AWS::URLSuffix") == "amazonaws.com"

    def test_context_get_method(self):
        """Test the get() method from base Context."""
        ctx = AWSContext(project="myapp", region="us-east-1")

        assert ctx.get("project") == "myapp"
        assert ctx.get("region") == "us-east-1"
        assert ctx.get("missing", "default") == "default"
