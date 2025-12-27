"""Tests for CloudFormationProvider."""

import pytest

from wetwire_aws import CloudFormationProvider
from wetwire_aws.resources.s3 import Bucket
from wetwire_aws.resources.iam import Role
from wetwire_aws.decorator import wetwire_aws, get_aws_registry


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear the registry before and after each test."""
    get_aws_registry().clear()
    yield
    get_aws_registry().clear()


# Define test wrapper classes at module level
@wetwire_aws
class ProviderTestBucket:
    resource: Bucket
    bucket_name = "test-bucket"


@wetwire_aws
class ProviderTestRole:
    resource: Role
    role_name = "test-role"


class TestCloudFormationProvider:
    """Test CloudFormationProvider implementation."""

    def test_provider_name(self):
        """Test that provider has correct name."""
        provider = CloudFormationProvider()
        assert provider.name == "cloudformation"

    def test_serialize_ref(self):
        """Test serializing a Ref to CloudFormation format."""
        provider = CloudFormationProvider()

        result = provider.serialize_ref(ProviderTestRole, ProviderTestBucket)
        assert result == {"Ref": "ProviderTestBucket"}

    def test_serialize_attr(self):
        """Test serializing an Attr to CloudFormation format."""
        provider = CloudFormationProvider()

        result = provider.serialize_attr(ProviderTestRole, ProviderTestBucket, "Arn")
        assert result == {"Fn::GetAtt": ["ProviderTestBucket", "Arn"]}

    def test_get_logical_id_default(self):
        """Test getting logical ID uses class name by default."""
        provider = CloudFormationProvider()

        result = provider.get_logical_id(ProviderTestBucket)
        assert result == "ProviderTestBucket"

    def test_get_logical_id_custom(self):
        """Test getting logical ID respects _logical_id attribute."""

        @wetwire_aws
        class CustomLogicalIdResource:
            resource: Bucket
            bucket_name = "custom"
            _logical_id = "MyCustomBucket"

        provider = CloudFormationProvider()
        result = provider.get_logical_id(CustomLogicalIdResource)
        assert result == "MyCustomBucket"

    def test_provider_repr(self):
        """Test provider repr."""
        provider = CloudFormationProvider()
        assert repr(provider) == "CloudFormationProvider(name='cloudformation')"


class TestProviderResourceSerialization:
    """Test CloudFormationProvider resource serialization."""

    def test_serialize_resource(self):
        """Test serializing a resource to CloudFormation format."""
        provider = CloudFormationProvider()
        instance = ProviderTestBucket()

        result = provider.serialize_resource(instance)

        assert result["Type"] == "AWS::S3::Bucket"
        assert "Properties" in result
        assert result["Properties"]["BucketName"] == "test-bucket"
