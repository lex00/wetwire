"""Tests for enum constants generated from botocore."""


class TestLambdaConstants:
    """Tests for Lambda constants."""

    def test_runtime_constants_exist(self):
        """Runtime constants are accessible."""
        from wetwire_aws.resources.lambda_ import Runtime

        assert Runtime.PYTHON3_12 == "python3.12"
        assert Runtime.NODEJS20_X == "nodejs20.x"
        assert Runtime.JAVA21 == "java21"

    def test_architecture_constants_exist(self):
        """Architecture constants are accessible."""
        from wetwire_aws.resources.lambda_ import Architecture

        assert Architecture.X86_64 == "x86_64"
        assert Architecture.ARM64 == "arm64"

    def test_package_type_constants_exist(self):
        """PackageType constants are accessible."""
        from wetwire_aws.resources.lambda_ import PackageType

        assert PackageType.ZIP == "Zip"
        assert PackageType.IMAGE == "Image"


class TestDynamoDBConstants:
    """Tests for DynamoDB constants."""

    def test_billing_mode_constants(self):
        """BillingMode constants are accessible."""
        from wetwire_aws.resources.dynamodb import BillingMode

        assert BillingMode.PROVISIONED == "PROVISIONED"
        assert BillingMode.PAY_PER_REQUEST == "PAY_PER_REQUEST"

    def test_stream_view_type_constants(self):
        """StreamViewType constants are accessible."""
        from wetwire_aws.resources.dynamodb import StreamViewType

        assert StreamViewType.KEYS_ONLY == "KEYS_ONLY"
        assert StreamViewType.NEW_IMAGE == "NEW_IMAGE"
        assert StreamViewType.OLD_IMAGE == "OLD_IMAGE"
        assert StreamViewType.NEW_AND_OLD_IMAGES == "NEW_AND_OLD_IMAGES"


class TestConstantsInResources:
    """Tests for using constants in resource definitions."""

    def test_lambda_function_with_runtime(self):
        """Lambda Function can use Runtime constant."""
        from wetwire_aws.resources.lambda_ import Function, Runtime

        func = Function(
            function_name="my-function",
            runtime=Runtime.PYTHON3_12,
        )

        data = func.to_dict()
        assert data["Properties"]["Runtime"] == "python3.12"

    def test_dynamodb_table_with_billing_mode(self):
        """DynamoDB Table can use BillingMode constant."""
        from wetwire_aws.resources.dynamodb import BillingMode, Table

        table = Table(
            table_name="my-table",
            billing_mode=BillingMode.PAY_PER_REQUEST,
        )

        data = table.to_dict()
        assert data["Properties"]["BillingMode"] == "PAY_PER_REQUEST"
