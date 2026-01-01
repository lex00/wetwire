package main

import (
	"github.com/wetwire-aws/s3"
)

// LogStorageBucket is an S3 bucket configured for log storage
// with AES-256 server-side encryption and blocked public access
var LogStorageBucket = s3.Bucket{
	BucketEncryption: &s3.BucketEncryption{
		ServerSideEncryptionConfiguration: []s3.ServerSideEncryptionRule{
			{
				ServerSideEncryptionByDefault: &s3.ServerSideEncryptionByDefault{
					SSEAlgorithm: "AES256",
				},
			},
		},
	},
	PublicAccessBlockConfiguration: &s3.PublicAccessBlockConfiguration{
		BlockPublicAcls:       true,
		BlockPublicPolicy:     true,
		IgnorePublicAcls:      true,
		RestrictPublicBuckets: true,
	},
}