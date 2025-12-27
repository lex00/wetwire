"""Tests for generated CloudFormation resources."""


class TestResourceImports:
    """Tests that generated resources can be imported."""

    def test_import_s3(self):
        """S3 resources can be imported."""
        from wetwire_aws.resources import s3

        assert hasattr(s3, "Bucket")
        assert s3.Bucket._resource_type == "AWS::S3::Bucket"

    def test_import_ec2(self):
        """EC2 resources can be imported."""
        from wetwire_aws.resources import ec2

        assert hasattr(ec2, "Instance")
        assert hasattr(ec2, "VPC")
        assert hasattr(ec2, "SecurityGroup")

    def test_import_iam(self):
        """IAM resources can be imported."""
        from wetwire_aws.resources import iam

        assert hasattr(iam, "Role")
        assert hasattr(iam, "Policy")
        assert hasattr(iam, "User")

    def test_import_lambda(self):
        """Lambda resources can be imported (with underscore)."""
        from wetwire_aws.resources import lambda_

        assert hasattr(lambda_, "Function")
        assert lambda_.Function._resource_type == "AWS::Lambda::Function"

    def test_import_dynamodb(self):
        """DynamoDB resources can be imported."""
        from wetwire_aws.resources import dynamodb

        assert hasattr(dynamodb, "Table")

    def test_import_sqs(self):
        """SQS resources can be imported."""
        from wetwire_aws.resources import sqs

        assert hasattr(sqs, "Queue")

    def test_import_sns(self):
        """SNS resources can be imported."""
        from wetwire_aws.resources import sns

        assert hasattr(sns, "Topic")


class TestS3Bucket:
    """Tests for S3 Bucket resource."""

    def test_bucket_creation(self):
        """S3 Bucket can be instantiated."""
        from wetwire_aws.resources.s3 import Bucket

        bucket = Bucket(bucket_name="my-test-bucket")
        assert bucket.bucket_name == "my-test-bucket"

    def test_bucket_to_dict(self):
        """S3 Bucket converts to dict."""
        from wetwire_aws.resources.s3 import Bucket

        bucket = Bucket(bucket_name="my-bucket")
        result = bucket.to_dict()

        assert result["Type"] == "AWS::S3::Bucket"
        assert result["Properties"]["BucketName"] == "my-bucket"

    def test_bucket_with_versioning(self):
        """S3 Bucket with versioning config."""
        from wetwire_aws.resources.s3 import Bucket, VersioningConfiguration

        bucket = Bucket(
            bucket_name="versioned-bucket",
            versioning_configuration=VersioningConfiguration(status="Enabled"),
        )
        result = bucket.to_dict()

        assert result["Properties"]["VersioningConfiguration"]["Status"] == "Enabled"


class TestLambdaFunction:
    """Tests for Lambda Function resource."""

    def test_function_creation(self):
        """Lambda Function can be instantiated."""
        from wetwire_aws.resources.lambda_ import Code, Function

        func = Function(
            function_name="my-function",
            runtime="python3.11",
            handler="index.handler",
            role="arn:aws:iam::123456789012:role/MyRole",
            code=Code(s3_bucket="my-bucket", s3_key="code.zip"),
        )

        assert func.function_name == "my-function"
        assert func.runtime == "python3.11"

    def test_function_to_dict(self):
        """Lambda Function converts to dict."""
        from wetwire_aws.resources.lambda_ import Code, Function

        func = Function(
            function_name="test-func",
            runtime="python3.11",
            handler="main.handler",
            role="arn:aws:iam::123456789012:role/Role",
            code=Code(s3_bucket="bucket", s3_key="key"),
        )
        result = func.to_dict()

        assert result["Type"] == "AWS::Lambda::Function"
        assert result["Properties"]["Runtime"] == "python3.11"


class TestIAMRole:
    """Tests for IAM Role resource."""

    def test_role_creation(self):
        """IAM Role can be instantiated."""
        from wetwire_aws.resources.iam import Role

        role = Role(
            role_name="MyRole",
            assume_role_policy_document={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            },
        )

        assert role.role_name == "MyRole"

    def test_role_to_dict(self):
        """IAM Role converts to dict."""
        from wetwire_aws.resources.iam import Role

        role = Role(
            assume_role_policy_document={"Version": "2012-10-17", "Statement": []},
        )
        result = role.to_dict()

        assert result["Type"] == "AWS::IAM::Role"
        assert "AssumeRolePolicyDocument" in result["Properties"]


class TestDynamoDBTable:
    """Tests for DynamoDB Table resource."""

    def test_table_creation(self):
        """DynamoDB Table can be instantiated."""
        from wetwire_aws.resources.dynamodb import (
            AttributeDefinition,
            KeySchema,
            Table,
        )

        table = Table(
            table_name="my-table",
            attribute_definitions=[
                AttributeDefinition(attribute_name="pk", attribute_type="S"),
            ],
            key_schema=[
                KeySchema(attribute_name="pk", key_type="HASH"),
            ],
            billing_mode="PAY_PER_REQUEST",
        )

        assert table.table_name == "my-table"
        assert table.billing_mode == "PAY_PER_REQUEST"


class TestPropertyTypes:
    """Tests for nested property types."""

    def test_property_type_instantiation(self):
        """Property types can be instantiated."""
        from wetwire_aws.resources.s3 import VersioningConfiguration

        config = VersioningConfiguration(status="Enabled")
        assert config.status == "Enabled"

    def test_property_type_to_dict(self):
        """Property types convert to dict."""
        from wetwire_aws.resources.s3 import VersioningConfiguration

        config = VersioningConfiguration(status="Enabled")
        result = config.to_dict()

        assert result == {"Status": "Enabled"}

    def test_nested_property_types(self):
        """Nested property types work correctly."""
        from wetwire_aws.resources.s3 import (
            BucketEncryption,
            ServerSideEncryptionByDefault,
            ServerSideEncryptionRule,
        )

        encryption = BucketEncryption(
            server_side_encryption_configuration=[
                ServerSideEncryptionRule(
                    server_side_encryption_by_default=ServerSideEncryptionByDefault(
                        sse_algorithm="AES256",
                    ),
                ),
            ],
        )

        result = encryption.to_dict()
        assert "ServerSideEncryptionConfiguration" in result


class TestResourceWithIntrinsics:
    """Tests for resources with intrinsic functions."""

    def test_bucket_with_sub(self):
        """S3 Bucket with Sub in name."""
        from wetwire_aws.intrinsics import Sub
        from wetwire_aws.resources.s3 import Bucket

        bucket = Bucket(bucket_name=Sub("${AWS::StackName}-data"))
        result = bucket.to_dict()

        assert result["Properties"]["BucketName"] == {
            "Fn::Sub": "${AWS::StackName}-data"
        }

    def test_function_with_refs(self):
        """Lambda with Ref for role."""
        from wetwire_aws.intrinsics import GetAtt, Ref
        from wetwire_aws.resources.lambda_ import Code, Function

        func = Function(
            function_name="test",
            runtime="python3.11",
            handler="index.handler",
            role=GetAtt("MyRole", "Arn"),
            code=Code(s3_bucket=Ref("CodeBucket"), s3_key="code.zip"),
        )
        result = func.to_dict()

        assert result["Properties"]["Role"] == {"Fn::GetAtt": ["MyRole", "Arn"]}
        assert result["Properties"]["Code"]["S3Bucket"] == {"Ref": "CodeBucket"}
