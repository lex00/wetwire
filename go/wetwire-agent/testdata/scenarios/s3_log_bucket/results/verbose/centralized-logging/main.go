package main

import (
	"github.com/wetwire-aws/kms"
	"github.com/wetwire-aws/s3"
)

// KMS key for encrypting logs with automatic rotation
var LogsKMSKey = kms.Key{
	Description: "KMS key for encrypting centralized application logs",
	KeyPolicy: map[string]interface{}{
		"Version": "2012-10-17",
		"Statement": []map[string]interface{}{
			{
				"Sid":    "Enable IAM User Permissions",
				"Effect": "Allow",
				"Principal": map[string]string{
					"AWS": "arn:aws:iam::${AWS::AccountId}:root",
				},
				"Action":   "kms:*",
				"Resource": "*",
			},
			{
				"Sid":    "Allow CloudWatch Logs",
				"Effect": "Allow",
				"Principal": map[string]string{
					"Service": "logs.amazonaws.com",
				},
				"Action": []string{
					"kms:Encrypt",
					"kms:Decrypt",
					"kms:ReEncrypt*",
					"kms:GenerateDataKey*",
					"kms:DescribeKey",
				},
				"Resource": "*",
				"Condition": map[string]interface{}{
					"ArnEquals": map[string]string{
						"kms:EncryptionContext:aws:logs:arn": "arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:*",
					},
				},
			},
			{
				"Sid":    "Allow application services to write logs",
				"Effect": "Allow",
				"Principal": map[string]string{
					"AWS": "arn:aws:iam::${AWS::AccountId}:role/*",
				},
				"Action": []string{
					"kms:Encrypt",
					"kms:GenerateDataKey",
					"kms:DescribeKey",
				},
				"Resource": "*",
				"Condition": map[string]interface{}{
					"StringLike": map[string]string{
						"kms:ViaService": "s3.${AWS::Region}.amazonaws.com",
					},
				},
			},
		},
	},
	KeyRotationEnabled: true,
}

// KMS key alias for easier reference
var LogsKMSKeyAlias = kms.Alias{
	AliasName:   "alias/centralized-logs-key",
	TargetKeyId: LogsKMSKey.Ref,
}

// S3 bucket for centralized log storage with comprehensive security and lifecycle policies
var CentralizedLogsBucket = s3.Bucket{
	BucketName: "${AWS::StackName}-centralized-logs-${AWS::Region}",
	BucketEncryption: map[string]interface{}{
		"ServerSideEncryptionConfiguration": []map[string]interface{}{
			{
				"ServerSideEncryptionByDefault": map[string]interface{}{
					"SSEAlgorithm":   "aws:kms",
					"KMSMasterKeyID": LogsKMSKey.Arn,
				},
				"BucketKeyEnabled": true, // Reduces KMS costs
			},
		},
	},
	PublicAccessBlockConfiguration: map[string]interface{}{
		"BlockPublicAcls":       true,
		"BlockPublicPolicy":     true,
		"IgnorePublicAcls":      true,
		"RestrictPublicBuckets": true,
	},
	VersioningConfiguration: map[string]interface{}{
		"Status": "Enabled",
	},
	LifecycleConfiguration: map[string]interface{}{
		"Rules": []map[string]interface{}{
			{
				"Id":     "LogsLifecycleRule",
				"Status": "Enabled",
				"Transitions": []map[string]interface{}{
					{
						"Days":         30,
						"StorageClass": "STANDARD_IA", // After 30 days, move to Infrequent Access
					},
					{
						"Days":         90,
						"StorageClass": "GLACIER", // After 90 days, move to Glacier for cheaper long-term storage
					},
					{
						"Days":         365,
						"StorageClass": "DEEP_ARCHIVE", // After 1 year, move to Deep Archive for maximum cost savings
					},
				},
				"ExpirationInDays": 2557, // Delete after 7 years (7 * 365 + 2 for leap years)
			},
			{
				"Id":                             "IncompleteMultipartUploadsCleanup",
				"Status":                         "Enabled",
				"AbortIncompleteMultipartUpload": map[string]interface{}{
					"DaysAfterInitiation": 7, // Clean up incomplete uploads after 7 days
				},
			},
			{
				"Id":     "DeleteMarkersCleanup",
				"Status": "Enabled",
				"NoncurrentVersionExpiration": map[string]interface{}{
					"NoncurrentDays": 30, // Remove old versions after 30 days
				},
			},
		},
	},
	NotificationConfiguration: map[string]interface{}{
		"CloudWatchConfigurations": []map[string]interface{}{
			{
				"Event": "s3:ObjectCreated:*",
				"CloudWatchConfiguration": map[string]interface{}{
					"LogGroupName": "/aws/s3/centralized-logs",
				},
			},
		},
	},
	LoggingConfiguration: map[string]interface{}{
		"DestinationBucketName": "${AWS::StackName}-centralized-logs-access-logs-${AWS::Region}",
		"LogFilePrefix":         "access-logs/",
	},
}

// Separate bucket for S3 access logs (following security best practices)
var AccessLogsBucket = s3.Bucket{
	BucketName: "${AWS::StackName}-centralized-logs-access-logs-${AWS::Region}",
	BucketEncryption: map[string]interface{}{
		"ServerSideEncryptionConfiguration": []map[string]interface{}{
			{
				"ServerSideEncryptionByDefault": map[string]interface{}{
					"SSEAlgorithm": "AES256",
				},
			},
		},
	},
	PublicAccessBlockConfiguration: map[string]interface{}{
		"BlockPublicAcls":       true,
		"BlockPublicPolicy":     true,
		"IgnorePublicAcls":      true,
		"RestrictPublicBuckets": true,
	},
	LifecycleConfiguration: map[string]interface{}{
		"Rules": []map[string]interface{}{
			{
				"Id":               "AccessLogsCleanup",
				"Status":           "Enabled",
				"ExpirationInDays": 90, // Keep access logs for 90 days
			},
		},
	},
}

// Bucket policy for the main logs bucket - restricts access and enforces encryption
var LogsBucketPolicy = s3.BucketPolicy{
	Bucket: CentralizedLogsBucket.Ref,
	PolicyDocument: map[string]interface{}{
		"Version": "2012-10-17",
		"Statement": []map[string]interface{}{
			{
				"Sid":    "DenyInsecureConnections",
				"Effect": "Deny",
				"Principal": "*",
				"Action":   "s3:*",
				"Resource": []string{
					CentralizedLogsBucket.Arn,
					CentralizedLogsBucket.Arn + "/*",
				},
				"Condition": map[string]interface{}{
					"Bool": map[string]string{
						"aws:SecureTransport": "false",
					},
				},
			},
			{
				"Sid":    "DenyUnencryptedObjectUploads",
				"Effect": "Deny",
				"Principal": "*",
				"Action":   "s3:PutObject",
				"Resource": CentralizedLogsBucket.Arn + "/*",
				"Condition": map[string]interface{}{
					"StringNotEquals": map[string]string{
						"s3:x-amz-server-side-encryption": "aws:kms",
					},
				},
			},
			{
				"Sid":    "DenyIncorrectEncryptionKey",
				"Effect": "Deny",
				"Principal": "*",
				"Action":   "s3:PutObject",
				"Resource": CentralizedLogsBucket.Arn + "/*",
				"Condition": map[string]interface{}{
					"StringNotEquals": map[string]string{
						"s3:x-amz-server-side-encryption-aws-kms-key-id": LogsKMSKey.Arn,
					},
				},
			},
		},
	},
}