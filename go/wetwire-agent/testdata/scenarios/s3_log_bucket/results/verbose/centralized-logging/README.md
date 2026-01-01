# Centralized Logging Infrastructure

This package creates a secure, cost-optimized S3-based centralized logging solution with the following features:

## Architecture Overview

- **Primary S3 Bucket**: Stores application logs with KMS encryption
- **Access Logs Bucket**: Stores S3 access logs for security auditing
- **KMS Key**: Customer-managed key with automatic rotation for encryption
- **IAM Roles**: Separate roles for log writers and readers with least privilege
- **Lifecycle Policies**: Automatic cost optimization and compliance retention
- **Monitoring**: CloudWatch alarms and dashboard for operational visibility

## Security Features

### Encryption
- All logs encrypted with customer-managed KMS key
- Automatic key rotation enabled
- Bucket policies enforce encryption in transit and at rest

### Access Control
- Public access completely blocked
- Separate IAM roles for write vs read access
- MFA required for log reader role
- Conditional access policies

### Auditing
- S3 access logs stored in separate bucket
- CloudWatch monitoring of unusual access patterns
- SNS alerts for security and cost anomalies

## Cost Optimization

### Lifecycle Management
- **0-30 days**: Standard storage for immediate access
- **30-90 days**: Infrequent Access (IA) for occasional access
- **90-365 days**: Glacier for long-term storage
- **1-7 years**: Deep Archive for compliance retention
- **After 7 years**: Automatic deletion

### Additional Cost Controls
- Bucket key enabled to reduce KMS request costs
- Incomplete multipart upload cleanup after 7 days
- Old version cleanup after 30 days
- CloudWatch alarms for size monitoring

## Usage

### For Application Integration

1. **EC2 Instances**: Attach the `LogWriterInstanceProfile` to your instances
2. **ECS Tasks**: Use the `LogWriterRoleArn` in your task definition
3. **Lambda Functions**: Use the `LogWriterRoleArn` as the execution role

### S3 Path Structure

Upload logs to: `s3://[BUCKET_NAME]/logs/[APPLICATION]/[YYYY]/[MM]/[DD]/[log_file]`

Example:
```
s3://my-stack-centralized-logs-us-east-1/logs/web-app/2024/01/15/application.log
s3://my-stack-centralized-logs-us-east-1/logs/api-service/2024/01/15/error.log
```

### Sample Application Code

#### AWS CLI
```bash
aws s3 cp application.log s3://[BUCKET_NAME]/logs/my-app/$(date +%Y/%m/%d)/ \
  --sse aws:kms \
  --sse-kms-key-id [KMS_KEY_ID]
```

#### Python (boto3)
```python
import boto3
from datetime import datetime

s3 = boto3.client('s3')
bucket_name = '[BUCKET_NAME]'
kms_key_id = '[KMS_KEY_ID]'

# Upload log file
s3.upload_file(
    'local-log.txt',
    bucket_name,
    f'logs/my-app/{datetime.now().strftime("%Y/%m/%d")}/log-{datetime.now().isoformat()}.txt',
    ExtraArgs={
        'ServerSideEncryption': 'aws:kms',
        'SSEKMSKeyId': kms_key_id
    }
)
```

#### Node.js (AWS SDK)
```javascript
const AWS = require('aws-sdk');
const s3 = new AWS.S3();

const params = {
    Bucket: '[BUCKET_NAME]',
    Key: `logs/my-app/${new Date().toISOString().slice(0,10).replace(/-/g, '/')}/app.log`,
    Body: logData,
    ServerSideEncryption: 'aws:kms',
    SSEKMSKeyId: '[KMS_KEY_ID]'
};

s3.upload(params, (err, data) => {
    if (err) console.error(err);
    else console.log('Log uploaded:', data.Location);
});
```

## Monitoring

### CloudWatch Dashboard
Access the monitoring dashboard at the URL provided in the stack outputs.

### Key Metrics Monitored
- Bucket size (cost management)
- Object count (performance)
- KMS key usage (security)
- Upload patterns (operational insights)

### Alerts
Alerts are sent to the SNS topic for:
- Bucket size exceeding 100GB
- Object count exceeding 1M objects
- Unusual KMS usage patterns

## Operations

### Log Analysis
To analyze logs, assume the `LogReaderRole` (requires MFA):

```bash
aws sts assume-role \
  --role-arn [LOG_READER_ROLE_ARN] \
  --role-session-name log-analysis \
  --serial-number [MFA_DEVICE_ARN] \
  --token-code [MFA_TOKEN]
```

### Emergency Access
In case of emergencies, root account can access all resources, but all access is logged.

### Cost Monitoring
Monitor costs through:
- CloudWatch dashboard
- AWS Cost Explorer with resource tags
- S3 storage class analysis

## Compliance

This setup addresses common compliance requirements:
- **Encryption**: All data encrypted in transit and at rest
- **Access Control**: Role-based access with MFA for sensitive operations
- **Auditing**: Complete access logs and monitoring
- **Retention**: Configurable retention periods (currently 7 years)
- **Data Integrity**: S3 versioning enabled for data recovery

## Troubleshooting

### Common Issues
1. **Access Denied**: Verify the role has proper permissions and KMS key access
2. **Encryption Errors**: Ensure using the correct KMS key ID
3. **Cost Alerts**: Review lifecycle policies and cleanup old data

### Support
For issues with this infrastructure, check:
1. CloudWatch logs for error details
2. CloudTrail for API call history  
3. S3 access logs for access patterns
4. Stack events in CloudFormation console