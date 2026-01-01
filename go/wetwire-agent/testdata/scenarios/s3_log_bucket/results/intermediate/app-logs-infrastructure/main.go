package main

import (
	"github.com/wetwire/wetwire-aws/s3"
)

// S3 bucket for storing application logs with security best practices
var AppLogsBucket = s3.Bucket{
	BucketName: "my-app-logs-bucket", // TODO: Update with your specific bucket name
	
	// Enable server-side encryption with S3 managed keys (SSE-S3)
	BucketEncryption: &s3.BucketEncryption{
		ServerSideEncryptionConfiguration: []s3.ServerSideEncryptionRule{
			{
				ServerSideEncryptionByDefault: &s3.ServerSideEncryptionByDefault{
					SSEAlgorithm: "AES256",
				},
			},
		},
	},
	
	// Block all public access for security
	PublicAccessBlockConfiguration: &s3.PublicAccessBlockConfiguration{
		BlockPublicAcls:       true,
		BlockPublicPolicy:     true,
		IgnorePublicAcls:      true,
		RestrictPublicBuckets: true,
	},
	
	// Enable versioning for data protection
	VersioningConfiguration: &s3.VersioningConfiguration{
		Status: "Enabled",
	},
	
	// Configure lifecycle policy to manage log retention and costs
	LifecycleConfiguration: &s3.BucketLifecycleConfiguration{
		Rules: []s3.LifecycleRule{
			{
				ID:     "LogRetentionPolicy",
				Status: "Enabled",
				
				// Transition to cheaper storage classes over time
				Transitions: []s3.Transition{
					{
						Days:         30,
						StorageClass: "STANDARD_IA", // Infrequent Access after 30 days
					},
					{
						Days:         90,
						StorageClass: "GLACIER", // Archive after 90 days
					},
				},
				
				// Delete old log files after 2 years
				Expiration: &s3.LifecycleExpiration{
					Days: 730,
				},
				
				// Clean up incomplete multipart uploads
				AbortIncompleteMultipartUpload: &s3.AbortIncompleteMultipartUpload{
					DaysAfterInitiation: 7,
				},
			},
		},
	},
	
	// Enable access logging to track bucket access (optional)
	LoggingConfiguration: &s3.LoggingConfiguration{
		DestinationBucketName: "my-access-logs-bucket", // TODO: Create separate bucket for access logs if needed
		LogFilePrefix:         "access-logs/",
	},
	
	// Add tags for organization and cost tracking
	Tags: []s3.Tag{
		{Key: "Purpose", Value: "ApplicationLogs"},
		{Key: "Environment", Value: "production"}, // TODO: Update with your environment
		{Key: "CostCenter", Value: "engineering"},  // TODO: Update with your cost center
	},
}