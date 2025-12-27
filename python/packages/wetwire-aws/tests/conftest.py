"""Pytest configuration and shared fixtures."""

from dataclasses import dataclass
from typing import ClassVar

import pytest

from wetwire_aws.base import CloudFormationResource, PropertyType


@dataclass
class MockBucketEncryption(PropertyType):
    """Mock nested property type for testing."""

    sse_algorithm: str
    kms_master_key_id: str | None = None


@dataclass
class MockBucket(CloudFormationResource):
    """Mock S3 bucket resource for testing."""

    _resource_type: ClassVar[str] = "AWS::S3::Bucket"

    bucket_name: str
    versioning_enabled: bool = False
    encryption: MockBucketEncryption | None = None
    tags: list[dict[str, str]] | None = None


@dataclass
class MockQueue(CloudFormationResource):
    """Mock SQS queue resource for testing."""

    _resource_type: ClassVar[str] = "AWS::SQS::Queue"

    queue_name: str
    visibility_timeout: int = 30


@pytest.fixture
def mock_bucket():
    """Create a mock S3 bucket."""
    return MockBucket(bucket_name="my-test-bucket")


@pytest.fixture
def mock_bucket_with_encryption():
    """Create a mock S3 bucket with encryption."""
    return MockBucket(
        bucket_name="encrypted-bucket",
        versioning_enabled=True,
        encryption=MockBucketEncryption(
            sse_algorithm="aws:kms",
            kms_master_key_id="alias/my-key",
        ),
    )


@pytest.fixture
def mock_queue():
    """Create a mock SQS queue."""
    return MockQueue(queue_name="my-test-queue", visibility_timeout=60)
