"""Storage resources: LogBucket - S3 bucket for application logs."""

from . import *  # noqa: F403


class LogBucketServerSideEncryptionByDefault:
    """Server-side encryption configuration for log bucket."""

    resource: s3.bucket.ServerSideEncryptionByDefault
    sse_algorithm = s3.ServerSideEncryption.AES256


class LogBucketServerSideEncryptionRule:
    """Encryption rule for log bucket."""

    resource: s3.bucket.ServerSideEncryptionRule
    server_side_encryption_by_default = LogBucketServerSideEncryptionByDefault


class LogBucketEncryption:
    """Bucket encryption configuration."""

    resource: s3.bucket.BucketEncryption
    server_side_encryption_configuration = [LogBucketServerSideEncryptionRule]


class LogBucketPublicAccessBlock:
    """Block all public access to the log bucket."""

    resource: s3.bucket.PublicAccessBlockConfiguration
    block_public_acls = True
    block_public_policy = True
    ignore_public_acls = True
    restrict_public_buckets = True


class LogBucket:
    """S3 bucket for storing application logs."""

    resource: s3.Bucket
    bucket_encryption = LogBucketEncryption
    public_access_block_configuration = LogBucketPublicAccessBlock
