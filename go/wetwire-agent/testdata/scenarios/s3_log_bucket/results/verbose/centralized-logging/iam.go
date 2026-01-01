package main

import (
	"github.com/wetwire-aws/iam"
)

// IAM role for applications to write logs to the centralized bucket
var LogWriterRole = iam.Role{
	RoleName: "${AWS::StackName}-log-writer-role",
	AssumeRolePolicyDocument: map[string]interface{}{
		"Version": "2012-10-17",
		"Statement": []map[string]interface{}{
			{
				"Effect": "Allow",
				"Principal": map[string]interface{}{
					"Service": []string{
						"ec2.amazonaws.com",
						"ecs-tasks.amazonaws.com",
						"lambda.amazonaws.com",
					},
				},
				"Action": "sts:AssumeRole",
			},
			// Allow cross-account access for multi-account setups
			{
				"Effect": "Allow",
				"Principal": map[string]string{
					"AWS": "arn:aws:iam::${AWS::AccountId}:root",
				},
				"Action": "sts:AssumeRole",
				"Condition": map[string]interface{}{
					"StringEquals": map[string]string{
						"sts:ExternalId": "${AWS::StackName}-log-writer",
					},
				},
			},
		},
	},
	Description: "Role for applications to write logs to the centralized logging bucket",
	Tags: []map[string]string{
		{
			"Key":   "Purpose",
			"Value": "CentralizedLogging",
		},
		{
			"Key":   "Environment",
			"Value": "${AWS::StackName}",
		},
	},
}

// IAM policy for writing logs to the bucket
var LogWriterPolicy = iam.Policy{
	PolicyName: "${AWS::StackName}-log-writer-policy",
	PolicyDocument: map[string]interface{}{
		"Version": "2012-10-17",
		"Statement": []map[string]interface{}{
			{
				"Sid":    "AllowLogWrites",
				"Effect": "Allow",
				"Action": []string{
					"s3:PutObject",
					"s3:PutObjectAcl",
				},
				"Resource": CentralizedLogsBucket.Arn + "/logs/*",
			},
			{
				"Sid":    "AllowBucketLocationAccess",
				"Effect": "Allow",
				"Action": []string{
					"s3:GetBucketLocation",
					"s3:ListBucket",
				},
				"Resource": CentralizedLogsBucket.Arn,
				"Condition": map[string]interface{}{
					"StringLike": map[string]string{
						"s3:prefix": "logs/*",
					},
				},
			},
			{
				"Sid":    "AllowKMSEncryption",
				"Effect": "Allow",
				"Action": []string{
					"kms:Encrypt",
					"kms:GenerateDataKey",
					"kms:DescribeKey",
				},
				"Resource": LogsKMSKey.Arn,
			},
		},
	},
	Description: "Policy allowing applications to write encrypted logs to the centralized bucket",
	Roles: []string{
		LogWriterRole.Ref,
	},
}

// IAM role for log analysis/reading (for operations teams)
var LogReaderRole = iam.Role{
	RoleName: "${AWS::StackName}-log-reader-role",
	AssumeRolePolicyDocument: map[string]interface{}{
		"Version": "2012-10-17",
		"Statement": []map[string]interface{}{
			{
				"Effect": "Allow",
				"Principal": map[string]interface{}{
					"AWS": []string{
						"arn:aws:iam::${AWS::AccountId}:root",
					},
				},
				"Action": "sts:AssumeRole",
				"Condition": map[string]interface{}{
					"Bool": map[string]string{
						"aws:MultiFactorAuthPresent": "true",
					},
				},
			},
		},
	},
	Description: "Role for operations teams to read logs from the centralized bucket",
	Tags: []map[string]string{
		{
			"Key":   "Purpose",
			"Value": "CentralizedLogging",
		},
		{
			"Key":   "Environment",
			"Value": "${AWS::StackName}",
		},
	},
}

// IAM policy for reading logs from the bucket
var LogReaderPolicy = iam.Policy{
	PolicyName: "${AWS::StackName}-log-reader-policy",
	PolicyDocument: map[string]interface{}{
		"Version": "2012-10-17",
		"Statement": []map[string]interface{}{
			{
				"Sid":    "AllowLogReads",
				"Effect": "Allow",
				"Action": []string{
					"s3:GetObject",
					"s3:GetObjectVersion",
				},
				"Resource": CentralizedLogsBucket.Arn + "/*",
			},
			{
				"Sid":    "AllowBucketListing",
				"Effect": "Allow",
				"Action": []string{
					"s3:ListBucket",
					"s3:GetBucketLocation",
					"s3:ListBucketVersions",
				},
				"Resource": CentralizedLogsBucket.Arn,
			},
			{
				"Sid":    "AllowKMSDecryption",
				"Effect": "Allow",
				"Action": []string{
					"kms:Decrypt",
					"kms:DescribeKey",
				},
				"Resource": LogsKMSKey.Arn,
			},
		},
	},
	Description: "Policy allowing operations teams to read logs from the centralized bucket",
	Roles: []string{
		LogReaderRole.Ref,
	},
}

// Instance profile for EC2 instances that need to write logs
var LogWriterInstanceProfile = iam.InstanceProfile{
	InstanceProfileName: "${AWS::StackName}-log-writer-instance-profile",
	Roles: []string{
		LogWriterRole.Ref,
	},
}