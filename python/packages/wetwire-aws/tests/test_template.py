"""Tests for CloudFormation template generation."""

import json
from dataclasses import dataclass
from typing import ClassVar

from wetwire_aws.base import CloudFormationResource
from wetwire_aws.intrinsics import Equals, GetAtt, Ref, Sub
from wetwire_aws.template import CloudFormationTemplate


@dataclass
class SampleBucket(CloudFormationResource):
    """Sample S3 bucket resource for testing."""

    _resource_type: ClassVar[str] = "AWS::S3::Bucket"
    bucket_name: str
    versioning_enabled: bool = False


@dataclass
class SampleQueue(CloudFormationResource):
    """Sample SQS queue resource for testing."""

    _resource_type: ClassVar[str] = "AWS::SQS::Queue"
    queue_name: str
    visibility_timeout: int = 30


@dataclass
class SampleFunction(CloudFormationResource):
    """Sample Lambda function resource for testing."""

    _resource_type: ClassVar[str] = "AWS::Lambda::Function"
    function_name: str
    runtime: str
    handler: str
    code_uri: str


class TestCloudFormationTemplate:
    """Tests for CloudFormationTemplate class."""

    def test_empty_template(self):
        """Empty template has correct structure."""
        template = CloudFormationTemplate(description="Test template")
        result = template.to_dict()

        assert result["AWSTemplateFormatVersion"] == "2010-09-09"
        assert result["Description"] == "Test template"
        assert result["Resources"] == {}

    def test_add_resource(self):
        """Adding a resource works correctly."""
        template = CloudFormationTemplate()
        bucket = SampleBucket(bucket_name="my-bucket")
        template.add_resource("MyBucket", bucket)

        result = template.to_dict()
        assert "MyBucket" in result["Resources"]
        assert result["Resources"]["MyBucket"]["Type"] == "AWS::S3::Bucket"

    def test_add_multiple_resources(self):
        """Adding multiple resources works correctly."""
        template = CloudFormationTemplate()
        template.add_resource("Bucket", SampleBucket(bucket_name="bucket"))
        template.add_resource("Queue", SampleQueue(queue_name="queue"))

        result = template.to_dict()
        assert len(result["Resources"]) == 2
        assert "Bucket" in result["Resources"]
        assert "Queue" in result["Resources"]

    def test_add_parameter(self):
        """Adding a parameter works correctly."""
        template = CloudFormationTemplate()
        template.add_parameter(
            "Environment",
            type="String",
            description="Deployment environment",
            allowed_values=["dev", "staging", "prod"],
            default="dev",
        )

        result = template.to_dict()
        assert "Parameters" in result
        assert "Environment" in result["Parameters"]
        assert result["Parameters"]["Environment"]["Type"] == "String"
        assert result["Parameters"]["Environment"]["Default"] == "dev"

    def test_add_output(self):
        """Adding an output works correctly."""
        template = CloudFormationTemplate()
        bucket = SampleBucket(bucket_name="my-bucket")
        template.add_resource("MyBucket", bucket)
        template.add_output(
            "BucketArn",
            value=GetAtt("MyBucket", "Arn"),
            description="The bucket ARN",
            export_name="MyStack-BucketArn",
        )

        result = template.to_dict()
        assert "Outputs" in result
        assert "BucketArn" in result["Outputs"]
        assert result["Outputs"]["BucketArn"]["Value"] == {
            "Fn::GetAtt": ["MyBucket", "Arn"]
        }
        assert result["Outputs"]["BucketArn"]["Export"]["Name"] == "MyStack-BucketArn"

    def test_add_condition(self):
        """Adding a condition works correctly."""
        template = CloudFormationTemplate()
        template.add_parameter("Environment", type="String", default="dev")
        template.add_condition("IsProd", Equals(Ref("Environment"), "prod"))

        result = template.to_dict()
        assert "Conditions" in result
        assert "IsProd" in result["Conditions"]

    def test_add_mapping(self):
        """Adding a mapping works correctly."""
        template = CloudFormationTemplate()
        template.add_mapping(
            "RegionMap",
            {
                "us-east-1": {"AMI": "ami-12345"},
                "us-west-2": {"AMI": "ami-67890"},
            },
        )

        result = template.to_dict()
        assert "Mappings" in result
        assert "RegionMap" in result["Mappings"]
        assert result["Mappings"]["RegionMap"]["us-east-1"]["AMI"] == "ami-12345"

    def test_to_json(self):
        """to_json() produces valid JSON."""
        template = CloudFormationTemplate(description="JSON test")
        template.add_resource("Bucket", SampleBucket(bucket_name="test"))

        json_str = template.to_json()
        parsed = json.loads(json_str)

        assert parsed["Description"] == "JSON test"
        assert "Bucket" in parsed["Resources"]

    def test_to_json_indent(self):
        """to_json() respects indent parameter."""
        template = CloudFormationTemplate()
        template.add_resource("Bucket", SampleBucket(bucket_name="test"))

        compact = template.to_json(indent=None)
        pretty = template.to_json(indent=2)

        assert "\n" not in compact
        assert "\n" in pretty

    def test_to_yaml(self):
        """to_yaml() produces valid YAML."""
        template = CloudFormationTemplate(description="YAML test")
        template.add_resource("Bucket", SampleBucket(bucket_name="test"))

        yaml_str = template.to_yaml()

        assert "AWSTemplateFormatVersion" in yaml_str
        assert "Description: YAML test" in yaml_str
        assert "Bucket:" in yaml_str

    def test_resource_with_depends_on(self):
        """Resource DependsOn is included."""
        template = CloudFormationTemplate()
        bucket = SampleBucket(bucket_name="bucket")
        queue = SampleQueue(queue_name="queue")
        queue.depends_on = [SampleBucket]

        template.add_resource("Bucket", bucket)
        template.add_resource("Queue", queue)

        result = template.to_dict()
        assert result["Resources"]["Queue"]["DependsOn"] == ["SampleBucket"]

    def test_resource_with_condition(self):
        """Resource Condition is included."""
        template = CloudFormationTemplate()
        template.add_parameter("CreateBucket", type="String", default="true")
        template.add_condition("ShouldCreate", Equals(Ref("CreateBucket"), "true"))

        bucket = SampleBucket(bucket_name="conditional-bucket")
        bucket.condition = "ShouldCreate"
        template.add_resource("Bucket", bucket)

        result = template.to_dict()
        assert result["Resources"]["Bucket"]["Condition"] == "ShouldCreate"

    def test_intrinsic_in_property(self):
        """Intrinsic functions in properties are serialized."""
        template = CloudFormationTemplate()
        template.add_parameter("BucketPrefix", type="String")

        bucket = SampleBucket(bucket_name=Sub("${BucketPrefix}-data"))
        template.add_resource("Bucket", bucket)

        result = template.to_dict()
        assert result["Resources"]["Bucket"]["Properties"]["BucketName"] == {
            "Fn::Sub": "${BucketPrefix}-data"
        }


class TestTemplateIntegration:
    """Integration tests for complete templates."""

    def test_complete_stack(self):
        """Complete stack with all components."""
        template = CloudFormationTemplate(
            description="Complete test stack",
            transform=["AWS::Serverless-2016-10-31"],
        )

        # Parameters
        template.add_parameter(
            "Environment",
            type="String",
            allowed_values=["dev", "prod"],
            default="dev",
        )

        # Conditions
        template.add_condition("IsProd", Equals(Ref("Environment"), "prod"))

        # Mappings
        template.add_mapping(
            "Config",
            {
                "dev": {"Retention": "7"},
                "prod": {"Retention": "30"},
            },
        )

        # Resources
        bucket = SampleBucket(
            bucket_name=Sub("${AWS::StackName}-data"),
            versioning_enabled=True,
        )
        template.add_resource("DataBucket", bucket)

        # Outputs
        template.add_output(
            "BucketName",
            value=Ref("DataBucket"),
            description="Name of the data bucket",
        )

        result = template.to_dict()

        # Verify structure
        assert result["AWSTemplateFormatVersion"] == "2010-09-09"
        assert result["Description"] == "Complete test stack"
        assert result["Transform"] == ["AWS::Serverless-2016-10-31"]
        assert "Parameters" in result
        assert "Conditions" in result
        assert "Mappings" in result
        assert "Resources" in result
        assert "Outputs" in result

    def test_template_validates_json(self):
        """Generated JSON is valid."""
        template = CloudFormationTemplate()
        template.add_resource("Bucket", SampleBucket(bucket_name="test"))
        template.add_resource("Queue", SampleQueue(queue_name="test"))

        json_str = template.to_json()

        # Should not raise
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
