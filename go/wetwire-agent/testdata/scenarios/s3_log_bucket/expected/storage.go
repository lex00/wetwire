// Package s3_log_bucket contains CloudFormation resources for log storage.
// Storage resources: LogBucket - S3 bucket for application logs.
package s3_log_bucket

import (
	"github.com/lex00/wetwire/go/wetwire-aws/resources/s3"
)

// LogBucketServerSideEncryptionByDefault configures AES-256 encryption.
var LogBucketServerSideEncryptionByDefault = &s3.Bucket_ServerSideEncryptionByDefault{
	SSEAlgorithm: "AES256",
}

// LogBucketServerSideEncryptionRule wraps the encryption configuration.
var LogBucketServerSideEncryptionRule = s3.Bucket_ServerSideEncryptionRule{
	ServerSideEncryptionByDefault: LogBucketServerSideEncryptionByDefault,
}

// LogBucketEncryption configures bucket encryption with AES-256.
var LogBucketEncryption = &s3.Bucket_BucketEncryption{
	ServerSideEncryptionConfiguration: []s3.Bucket_ServerSideEncryptionRule{
		LogBucketServerSideEncryptionRule,
	},
}

// LogBucketPublicAccessBlock blocks all public access to the log bucket.
var LogBucketPublicAccessBlock = &s3.Bucket_PublicAccessBlockConfiguration{
	BlockPublicAcls:       true,
	BlockPublicPolicy:     true,
	IgnorePublicAcls:      true,
	RestrictPublicBuckets: true,
}

// LogBucket is an S3 bucket for storing application logs.
var LogBucket = s3.Bucket{
	BucketEncryption:               LogBucketEncryption,
	PublicAccessBlockConfiguration: LogBucketPublicAccessBlock,
}
