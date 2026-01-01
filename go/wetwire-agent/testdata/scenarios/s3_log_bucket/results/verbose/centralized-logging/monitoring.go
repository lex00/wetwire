package main

import (
	"github.com/wetwire-aws/cloudwatch"
	"github.com/wetwire-aws/sns"
)

// SNS topic for logging-related alerts
var LoggingAlertsTopic = sns.Topic{
	TopicName:   "${AWS::StackName}-logging-alerts",
	DisplayName: "Centralized Logging Alerts",
	KmsMasterKeyId: LogsKMSKey.Ref,
}

// CloudWatch alarm for monitoring bucket size (cost management)
var BucketSizeAlarm = cloudwatch.Alarm{
	AlarmName:          "${AWS::StackName}-logs-bucket-size-high",
	AlarmDescription:   "Alert when the centralized logs bucket size exceeds threshold",
	MetricName:         "BucketSizeBytes",
	Namespace:          "AWS/S3",
	Statistic:          "Average",
	Period:             86400, // 24 hours
	EvaluationPeriods:  1,
	Threshold:          107374182400, // 100 GB in bytes
	ComparisonOperator: "GreaterThanThreshold",
	Dimensions: []map[string]string{
		{
			"Name":  "BucketName",
			"Value": CentralizedLogsBucket.Ref,
		},
		{
			"Name":  "StorageType",
			"Value": "StandardStorage",
		},
	},
	AlarmActions: []string{
		LoggingAlertsTopic.Ref,
	},
	TreatMissingData: "notBreaching",
}

// CloudWatch alarm for monitoring number of objects (performance)
var ObjectCountAlarm = cloudwatch.Alarm{
	AlarmName:          "${AWS::StackName}-logs-object-count-high",
	AlarmDescription:   "Alert when the number of objects in logs bucket is very high",
	MetricName:         "NumberOfObjects",
	Namespace:          "AWS/S3",
	Statistic:          "Average",
	Period:             86400, // 24 hours
	EvaluationPeriods:  1,
	Threshold:          1000000, // 1 million objects
	ComparisonOperator: "GreaterThanThreshold",
	Dimensions: []map[string]string{
		{
			"Name":  "BucketName",
			"Value": CentralizedLogsBucket.Ref,
		},
		{
			"Name":  "StorageType",
			"Value": "AllStorageTypes",
		},
	},
	AlarmActions: []string{
		LoggingAlertsTopic.Ref,
	},
	TreatMissingData: "notBreaching",
}

// CloudWatch alarm for KMS key usage (security monitoring)
var KMSUsageAlarm = cloudwatch.Alarm{
	AlarmName:          "${AWS::StackName}-kms-usage-anomaly",
	AlarmDescription:   "Alert on unusual KMS key usage patterns for logs encryption",
	MetricName:         "NumberOfRequestsSucceeded",
	Namespace:          "AWS/KMS",
	Statistic:          "Sum",
	Period:             3600, // 1 hour
	EvaluationPeriods:  2,
	Threshold:          10000, // Adjust based on your expected usage
	ComparisonOperator: "GreaterThanThreshold",
	Dimensions: []map[string]string{
		{
			"Name":  "KeyId",
			"Value": LogsKMSKey.Ref,
		},
	},
	AlarmActions: []string{
		LoggingAlertsTopic.Ref,
	},
	TreatMissingData: "notBreaching",
}

// CloudWatch log group for S3 bucket notifications (if needed for debugging)
var S3NotificationsLogGroup = cloudwatch.LogGroup{
	LogGroupName:     "/aws/s3/centralized-logs",
	RetentionInDays:  14, // Keep S3 notifications for 2 weeks
	KmsKeyId:         LogsKMSKey.Arn,
}

// Custom metric filter to track log upload patterns
var LogUploadMetricFilter = cloudwatch.MetricFilter{
	LogGroupName: S3NotificationsLogGroup.Ref,
	FilterName:   "${AWS::StackName}-log-upload-pattern",
	FilterPattern: "[timestamp, request_id, event_name=\"ObjectCreated:Put\", ...]",
	MetricTransformations: []map[string]interface{}{
		{
			"MetricName":      "LogUploadsPerHour",
			"MetricNamespace": "CentralizedLogging/Usage",
			"MetricValue":     "1",
			"DefaultValue":    0,
		},
	},
}

// Dashboard for monitoring the logging infrastructure
var LoggingDashboard = cloudwatch.Dashboard{
	DashboardName: "${AWS::StackName}-centralized-logging",
	DashboardBody: map[string]interface{}{
		"widgets": []map[string]interface{}{
			{
				"type":   "metric",
				"x":      0,
				"y":      0,
				"width":  12,
				"height": 6,
				"properties": map[string]interface{}{
					"metrics": [][]interface{}{
						{"AWS/S3", "BucketSizeBytes", "BucketName", CentralizedLogsBucket.Ref, "StorageType", "StandardStorage"},
						{".", "NumberOfObjects", ".", ".", "StorageType", "AllStorageTypes"},
					},
					"period": 300,
					"stat":   "Average",
					"region": "${AWS::Region}",
					"title":  "Bucket Metrics",
					"view":   "timeSeries",
					"yAxis": map[string]interface{}{
						"left": map[string]interface{}{
							"min": 0,
						},
					},
				},
			},
			{
				"type":   "metric",
				"x":      12,
				"y":      0,
				"width":  12,
				"height": 6,
				"properties": map[string]interface{}{
					"metrics": [][]interface{}{
						{"AWS/KMS", "NumberOfRequestsSucceeded", "KeyId", LogsKMSKey.Ref},
						{".", "NumberOfRequestsFailed", ".", "."},
					},
					"period": 300,
					"stat":   "Sum",
					"region": "${AWS::Region}",
					"title":  "KMS Usage",
					"view":   "timeSeries",
				},
			},
			{
				"type":   "metric",
				"x":      0,
				"y":      6,
				"width":  24,
				"height": 6,
				"properties": map[string]interface{}{
					"metrics": [][]interface{}{
						{"CentralizedLogging/Usage", "LogUploadsPerHour"},
					},
					"period": 3600,
					"stat":   "Sum",
					"region": "${AWS::Region}",
					"title":  "Log Upload Activity",
					"view":   "timeSeries",
				},
			},
		},
	},
}