"""Tests for base CloudFormation classes."""

from dataclasses import dataclass

from wetwire_aws.base import PropertyType


class TestPropertyType:
    """Tests for PropertyType base class."""

    def test_property_type_to_dict(self):
        """PropertyType converts to dict correctly."""

        @dataclass
        class TestProp(PropertyType):
            name: str
            value: int

        prop = TestProp(name="test", value=42)
        result = prop.to_dict()

        assert result == {"Name": "test", "Value": 42}

    def test_property_type_nested(self):
        """Nested PropertyTypes convert correctly."""

        @dataclass
        class Inner(PropertyType):
            key: str

        @dataclass
        class Outer(PropertyType):
            inner: Inner
            label: str

        outer = Outer(inner=Inner(key="secret"), label="wrapper")
        result = outer.to_dict()

        assert result == {"Inner": {"Key": "secret"}, "Label": "wrapper"}

    def test_property_type_with_none(self):
        """None values are excluded from output."""

        @dataclass
        class OptionalProp(PropertyType):
            required: str
            optional: str | None = None

        prop = OptionalProp(required="yes")
        result = prop.to_dict()

        assert result == {"Required": "yes"}
        assert "Optional" not in result

    def test_property_type_with_list(self):
        """List values convert correctly."""

        @dataclass
        class ListProp(PropertyType):
            items: list[str]

        prop = ListProp(items=["a", "b", "c"])
        result = prop.to_dict()

        assert result == {"Items": ["a", "b", "c"]}

    def test_property_type_with_nested_list(self):
        """List of PropertyTypes convert correctly."""

        @dataclass
        class Item(PropertyType):
            name: str

        @dataclass
        class Container(PropertyType):
            items: list[Item]

        container = Container(items=[Item(name="one"), Item(name="two")])
        result = container.to_dict()

        assert result == {"Items": [{"Name": "one"}, {"Name": "two"}]}


class TestCloudFormationResource:
    """Tests for CloudFormationResource base class."""

    def test_resource_type(self, mock_bucket):
        """Resource has correct type."""
        assert mock_bucket._resource_type == "AWS::S3::Bucket"

    def test_resource_to_dict_basic(self, mock_bucket):
        """Resource converts to CloudFormation dict."""
        result = mock_bucket.to_dict()

        assert result["Type"] == "AWS::S3::Bucket"
        assert result["Properties"]["BucketName"] == "my-test-bucket"
        assert result["Properties"]["VersioningEnabled"] is False

    def test_resource_to_dict_with_nested(self, mock_bucket_with_encryption):
        """Resource with nested PropertyType converts correctly."""
        result = mock_bucket_with_encryption.to_dict()

        assert result["Properties"]["Encryption"] == {
            "SseAlgorithm": "aws:kms",
            "KmsMasterKeyId": "alias/my-key",
        }

    def test_resource_with_depends_on(self, mock_bucket, mock_queue):
        """DependsOn is included in output."""
        mock_bucket.depends_on = [type(mock_queue)]
        result = mock_bucket.to_dict()

        assert result["DependsOn"] == ["MockQueue"]

    def test_resource_with_condition(self, mock_bucket):
        """Condition is included in output."""
        mock_bucket.condition = "IsProduction"
        result = mock_bucket.to_dict()

        assert result["Condition"] == "IsProduction"

    def test_resource_with_metadata(self, mock_bucket):
        """Metadata is included in output."""
        mock_bucket.metadata = {"cfn-lint": {"config": {"ignore_checks": ["W3002"]}}}
        result = mock_bucket.to_dict()

        assert result["Metadata"] == {
            "cfn-lint": {"config": {"ignore_checks": ["W3002"]}}
        }

    def test_resource_none_properties_excluded(self, mock_bucket):
        """None property values are excluded."""
        result = mock_bucket.to_dict()

        assert "Encryption" not in result["Properties"]
        assert "Tags" not in result["Properties"]

    def test_resource_logical_name(self, mock_bucket):
        """Resource class name is used as logical name."""
        assert type(mock_bucket).__name__ == "MockBucket"


class TestSnakeToPascal:
    """Tests for snake_case to PascalCase conversion."""

    def test_simple_conversion(self):
        """Simple snake_case converts correctly."""

        @dataclass
        class Test(PropertyType):
            bucket_name: str

        prop = Test(bucket_name="test")
        result = prop.to_dict()

        assert "BucketName" in result

    def test_single_word(self):
        """Single word converts correctly."""

        @dataclass
        class Test(PropertyType):
            name: str

        prop = Test(name="test")
        result = prop.to_dict()

        assert "Name" in result

    def test_multiple_underscores(self):
        """Multiple underscores convert correctly."""

        @dataclass
        class Test(PropertyType):
            my_long_property_name: str

        prop = Test(my_long_property_name="test")
        result = prop.to_dict()

        assert "MyLongPropertyName" in result

    def test_with_numbers(self):
        """Properties with numbers convert correctly."""

        @dataclass
        class Test(PropertyType):
            ec2_instance_id: str

        prop = Test(ec2_instance_id="i-123")
        result = prop.to_dict()

        assert "Ec2InstanceId" in result

    def test_trailing_underscore_stripped(self):
        """Trailing underscore (Python keyword escape) is stripped."""

        @dataclass
        class Test(PropertyType):
            type_: str
            class_: str

        prop = Test(type_="test", class_="MyClass")
        result = prop.to_dict()

        assert "Type" in result
        assert "Class" in result
