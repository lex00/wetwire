from . import *

class LogBucketEncryptionDefault:
    resource: s3.bucket.ServerSideEncryptionByDefault
    sse_algorithm = s3.ServerSideEncryption.AES256

class LogBucketEncryptionRule:
    resource: s3.bucket.ServerSideEncryptionRule
    server_side_encryption_by_default = LogBucketEncryptionDefault

class LogBucketEncryption:
    resource: s3.bucket.BucketEncryption
    server_side_encryption_configuration = [LogBucketEncryptionRule]

class LogBucketPublicAccessBlock:
    resource: s3.bucket.PublicAccessBlockConfiguration
    block_public_acls = True
    block_public_policy = True
    ignore_public_acls = True
    restrict_public_buckets = True

class LogArchiveTransition:
    resource: s3.bucket.Transition
    storage_class = s3.StorageClass.GLACIER
    transition_in_days = 90

class LogDeleteRule:
    resource: s3.bucket.Rule
    id = "DeleteOldLogs"
    status = s3.BucketVersioningStatus.ENABLED
    expiration_in_days = 2555  # 7 years retention
    transitions = [LogArchiveTransition]

class LogBucketLifecycle:
    resource: s3.bucket.LifecycleConfiguration
    rules = [LogDeleteRule]

class ApplicationLogBucket:
    resource: s3.Bucket
    bucket_name = "application-logs-${AWS::AccountId}-${AWS::Region}"
    bucket_encryption = LogBucketEncryption
    public_access_block_configuration = LogBucketPublicAccessBlock
    lifecycle_configuration = LogBucketLifecycle