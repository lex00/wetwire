package intrinsics

// Pseudo-parameters are predefined by CloudFormation and available in every template.
// They return values specific to the current stack.
//
// Usage:
//
//	region := AWS_REGION           // {"Ref": "AWS::Region"}
//	arn := Sub{fmt.Sprintf("arn:aws:s3:::%s/*", AWS_ACCOUNT_ID)}
var (
	// AWS_ACCOUNT_ID returns the AWS account ID of the account in which the stack is created.
	AWS_ACCOUNT_ID = Ref{"AWS::AccountId"}

	// AWS_NOTIFICATION_ARNS returns the list of notification ARNs for the current stack.
	AWS_NOTIFICATION_ARNS = Ref{"AWS::NotificationARNs"}

	// AWS_NO_VALUE removes the resource property when used with Fn::If.
	AWS_NO_VALUE = Ref{"AWS::NoValue"}

	// AWS_PARTITION returns the partition the resource is in (aws, aws-cn, aws-us-gov).
	AWS_PARTITION = Ref{"AWS::Partition"}

	// AWS_REGION returns the AWS Region in which the stack is created.
	AWS_REGION = Ref{"AWS::Region"}

	// AWS_STACK_ID returns the ID of the stack.
	AWS_STACK_ID = Ref{"AWS::StackId"}

	// AWS_STACK_NAME returns the name of the stack.
	AWS_STACK_NAME = Ref{"AWS::StackName"}

	// AWS_URL_SUFFIX returns the suffix for a domain (usually amazonaws.com).
	AWS_URL_SUFFIX = Ref{"AWS::URLSuffix"}
)
