package main

import (
	"github.com/wetwire-aws/cloudformation"
)

// Outputs for easy integration with applications and other infrastructure
var Outputs = []cloudformation.Output{
	{
		Key:         "CentralizedLogsBucketName",
		Value:       CentralizedLogsBucket.Ref,
		Description: "Name of the centralized logs S3 bucket",
		Export: &cloudformation.Export{
			Name: "${AWS::StackName}-CentralizedLogsBucket",
		},
	},
	{
		Key:         "CentralizedLogsBucketArn",
		Value:       CentralizedLogsBucket.Arn,
		Description: "ARN of the centralized logs S3 bucket",
		Export: &cloudformation.Export{
			Name: "${AWS::StackName}-CentralizedLogsBucketArn",
		},
	},
	{
		Key:         "LogsKMSKeyId",
		Value:       LogsKMSKey.Ref,
		Description: "ID of the KMS key used for encrypting logs",
		Export: &cloudformation.Export{
			Name: "${AWS::StackName}-LogsKMSKey",
		},
	},
	{
		Key:         "LogsKMSKeyArn",
		Value:       LogsKMSKey.Arn,
		Description: "ARN of the KMS key used for encrypting logs",
		Export: &cloudformation.Export{
			Name: "${AWS::StackName}-LogsKMSKeyArn",
		},
	},
	{
		Key:         "LogsKMSKeyAlias",
		Value:       LogsKMSKeyAlias.Ref,
		Description: "Alias of the KMS key for easier reference",
		Export: &cloudformation.Export{
			Name: "${AWS::StackName}-LogsKMSKeyAlias",
		},
	},
	{
		Key:         "LogWriterRoleArn",
		Value:       LogWriterRole.Arn,
		Description: "ARN of the IAM role for applications to write logs",
		Export: &cloudformation.Export{
			Name: "${AWS::StackName}-LogWriterRole",
		},
	},
	{
		Key:         "LogReaderRoleArn",
		Value:       LogReaderRole.Arn,
		Description: "ARN of the IAM role for reading logs (operations team)",
		Export: &cloudformation.Export{
			Name: "${AWS::StackName}-LogReaderRole",
		},
	},
	{
		Key:         "LogWriterInstanceProfile",
		Value:       LogWriterInstanceProfile.Ref,
		Description: "Instance profile for EC2 instances that need to write logs",
		Export: &cloudformation.Export{
			Name: "${AWS::StackName}-LogWriterInstanceProfile",
		},
	},
	{
		Key:         "LoggingAlertsTopicArn",
		Value:       LoggingAlertsTopic.Ref,
		Description: "SNS topic ARN for logging infrastructure alerts",
		Export: &cloudformation.Export{
			Name: "${AWS::StackName}-LoggingAlertsTopic",
		},
	},
	{
		Key:         "LoggingDashboardURL",
		Value:       "https://" + "${AWS::Region}" + ".console.aws.amazon.com/cloudwatch/home?region=" + "${AWS::Region}" + "#dashboards:name=" + LoggingDashboard.Ref,
		Description: "URL to the CloudWatch dashboard for monitoring logging infrastructure",
	},
}