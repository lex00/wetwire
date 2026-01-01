package main

import (
	"github.com/wetwire/wetwire-aws/s3"
	"github.com/wetwire/wetwire-aws/iam"
)

// Access logs bucket - stores access logs for the main bucket
var AccessLogsBucket = s3.Bucket{
	BucketName: "app-logs-access-logs-${AWS::AccountId}-${AWS::Region}",
	PublicAccessBlockConfiguration: &s3.PublicAccessBlockConfiguration{
		BlockPublicAcls:       true,
		BlockPublicPolicy:     true,
		IgnorePublicAcls:      true,
		RestrictPublicBuckets: true,
	},
	BucketEncryption: &s3.BucketEncryption{
		ServerSideEncryptionConfiguration: []s3.ServerSideEncryptionRule{
			{
				ServerSideEncryptionByDefault: &s3.ServerSideEncryptionByDefault{
					SSEAlgorithm: "AES256",
				},
				BucketKeyEnabled: true,
			},
		},
	},
}

// Main log storage bucket
var LogsBucket = s3.Bucket{
	BucketName: "app-logs-storage-${AWS::AccountId}-${AWS::Region}",
	
	// Block all public access
	PublicAccessBlockConfiguration: &s3.PublicAccessBlockConfiguration{
		BlockPublicAcls:       true,
		BlockPublicPolicy:     true,
		IgnorePublicAcls:      true,
		RestrictPublicBuckets: true,
	},
	
	// Enable server-side encryption
	BucketEncryption: &s3.BucketEncryption{
		ServerSideEncryptionConfiguration: []s3.ServerSideEncryptionRule{
			{
				ServerSideEncryptionByDefault: &s3.ServerSideEncryptionByDefault{
					SSEAlgorithm: "AES256",
				},
				BucketKeyEnabled: true,
			},
		},
	},
	
	// Enable versioning for additional protection
	VersioningConfiguration: &s3.VersioningConfiguration{
		Status: "Enabled",
	},
	
	// Configure lifecycle to manage costs and compliance
	LifecycleConfiguration: &s3.LifecycleConfiguration{
		Rules: []s3.LifecycleRule{
			{
				Id:     "LogRetentionRule",
				Status: "Enabled",
				ExpirationInDays: 90,
				NoncurrentVersionExpirationInDays: 30,
			},
		},
	},
	
	// Enable access logging
	LoggingConfiguration: &s3.LoggingConfiguration{
		DestinationBucketName: AccessLogsBucket.Ref,
		LogFilePrefix:        "access-logs/",
	},
	
	// Enable notifications (optional - for monitoring)
	NotificationConfiguration: &s3.NotificationConfiguration{
		CloudWatchConfigurations: []s3.CloudWatchConfiguration{
			{
				Event: "s3:ObjectCreated:*",
			},
		},
	},
}

// IAM role for application to write logs
var AppLogWriterRole = iam.Role{
	RoleName: "AppLogWriterRole",
	AssumeRolePolicyDocument: map[string]interface{}{
		"Version": "2012-10-17",
		"Statement": []map[string]interface{}{
			{
				"Effect": "Allow",
				"Principal": map[string]interface{}{
					"Service": "ec2.amazonaws.com", // Adjust based on your application type
				},
				"Action": "sts:AssumeRole",
			},
		},
	},
}

// IAM policy allowing write access to logs bucket
var AppLogWriterPolicy = iam.Policy{
	PolicyName: "AppLogWriterPolicy",
	Roles: []string{AppLogWriterRole.Ref},
	PolicyDocument: map[string]interface{}{
		"Version": "2012-10-17",
		"Statement": []map[string]interface{}{
			{
				"Effect": "Allow",
				"Action": []string{
					"s3:PutObject",
					"s3:PutObjectAcl",
				},
				"Resource": LogsBucket.Arn + "/*",
			},
			{
				"Effect": "Allow",
				"Action": []string{
					"s3:ListBucket",
				},
				"Resource": LogsBucket.Arn,
			},
		},
	},
}