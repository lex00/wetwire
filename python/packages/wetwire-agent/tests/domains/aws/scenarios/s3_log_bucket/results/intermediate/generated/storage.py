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

class LogBucketVersioning:
    resource: s3.bucket.VersioningConfiguration
    status = s3.BucketVersioningStatus.ENABLED

class LogBucketLifecycleTransition:
    resource: s3.bucket.Transition
    storage_class = "STANDARD_IA"
    transition_in_days = 30

class LogBucketLifecycleRule:
    resource: s3.bucket.Rule
    id = "LogRetentionRule"
    status = s3.BucketVersioningStatus.ENABLED
    expiration_in_days = 2555  # 7 years
    transitions = [LogBucketLifecycleTransition]

class LogBucketLifecycle:
    resource: s3.bucket.LifecycleConfiguration
    rules = [LogBucketLifecycleRule]

class LogBucket:
    resource: s3.Bucket
    bucket_encryption = LogBucketEncryption
    public_access_block_configuration = LogBucketPublicAccessBlock
    versioning_configuration = LogBucketVersioning
    lifecycle_configuration = LogBucketLifecycle