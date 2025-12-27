"""Tests for CloudFormation intrinsic functions."""

from wetwire_aws.intrinsics import (
    # Pseudo-parameters
    AWS_ACCOUNT_ID,
    AWS_NO_VALUE,
    AWS_PARTITION,
    AWS_REGION,
    AWS_STACK_ID,
    AWS_STACK_NAME,
    AWS_URL_SUFFIX,
    And,
    Base64,
    Cidr,
    Equals,
    FindInMap,
    GetAtt,
    GetAZs,
    If,
    ImportValue,
    Join,
    Not,
    Or,
    # Functions
    Ref,
    Select,
    Split,
    Sub,
    get_att,
    # Helpers
    ref,
)


class TestRef:
    """Tests for Ref intrinsic function."""

    def test_ref_to_dict(self):
        """Ref converts to correct dict format."""
        r = Ref("MyBucket")
        assert r.to_dict() == {"Ref": "MyBucket"}

    def test_ref_helper(self):
        """ref() helper creates Ref from class."""
        from dataclasses import dataclass

        from wetwire_aws.base import CloudFormationResource

        @dataclass
        class MyBucket(CloudFormationResource):
            _resource_type = "AWS::S3::Bucket"
            bucket_name: str

        r = ref(MyBucket)
        assert r.to_dict() == {"Ref": "MyBucket"}


class TestGetAtt:
    """Tests for GetAtt intrinsic function."""

    def test_getatt_to_dict(self):
        """GetAtt converts to correct dict format."""
        ga = GetAtt("MyBucket", "Arn")
        assert ga.to_dict() == {"Fn::GetAtt": ["MyBucket", "Arn"]}

    def test_getatt_helper(self):
        """get_att() helper creates GetAtt from class."""
        from dataclasses import dataclass

        from wetwire_aws.base import CloudFormationResource

        @dataclass
        class MyBucket(CloudFormationResource):
            _resource_type = "AWS::S3::Bucket"
            bucket_name: str

        ga = get_att(MyBucket, "Arn")
        assert ga.to_dict() == {"Fn::GetAtt": ["MyBucket", "Arn"]}


class TestSub:
    """Tests for Sub intrinsic function."""

    def test_sub_simple(self):
        """Sub with simple string."""
        s = Sub("arn:aws:s3:::${BucketName}")
        assert s.to_dict() == {"Fn::Sub": "arn:aws:s3:::${BucketName}"}

    def test_sub_with_variables(self):
        """Sub with variable map."""
        s = Sub("${Domain}/api", {"Domain": "example.com"})
        assert s.to_dict() == {"Fn::Sub": ["${Domain}/api", {"Domain": "example.com"}]}


class TestJoin:
    """Tests for Join intrinsic function."""

    def test_join_simple(self):
        """Join with simple strings."""
        j = Join(",", ["a", "b", "c"])
        assert j.to_dict() == {"Fn::Join": [",", ["a", "b", "c"]]}

    def test_join_with_refs(self):
        """Join with Ref values."""
        j = Join("-", [Ref("Env"), "bucket"])
        result = j.to_dict()
        assert result["Fn::Join"][0] == "-"
        assert result["Fn::Join"][1][0] == {"Ref": "Env"}
        assert result["Fn::Join"][1][1] == "bucket"


class TestSelect:
    """Tests for Select intrinsic function."""

    def test_select(self):
        """Select picks from list (index is string per CF spec)."""
        s = Select(1, ["a", "b", "c"])
        # CloudFormation requires index as string
        assert s.to_dict() == {"Fn::Select": ["1", ["a", "b", "c"]]}


class TestConditionals:
    """Tests for conditional intrinsic functions."""

    def test_if(self):
        """If condition."""
        i = If("IsProduction", "prod-value", "dev-value")
        assert i.to_dict() == {"Fn::If": ["IsProduction", "prod-value", "dev-value"]}

    def test_equals(self):
        """Equals condition."""
        e = Equals(Ref("Env"), "prod")
        result = e.to_dict()
        assert result["Fn::Equals"][0] == {"Ref": "Env"}
        assert result["Fn::Equals"][1] == "prod"

    def test_and(self):
        """And condition."""
        a = And([Equals("a", "a"), Equals("b", "b")])
        result = a.to_dict()
        assert "Fn::And" in result
        assert len(result["Fn::And"]) == 2

    def test_or(self):
        """Or condition."""
        o = Or([Equals("a", "a"), Equals("b", "b")])
        result = o.to_dict()
        assert "Fn::Or" in result
        assert len(result["Fn::Or"]) == 2

    def test_not(self):
        """Not condition."""
        n = Not(Equals("a", "b"))
        result = n.to_dict()
        assert "Fn::Not" in result


class TestBase64:
    """Tests for Base64 intrinsic function."""

    def test_base64_simple(self):
        """Base64 with simple string."""
        b = Base64("hello world")
        assert b.to_dict() == {"Fn::Base64": "hello world"}

    def test_base64_with_sub(self):
        """Base64 with Sub."""
        b = Base64(Sub("#!/bin/bash\necho ${Message}"))
        result = b.to_dict()
        assert "Fn::Base64" in result


class TestGetAZs:
    """Tests for GetAZs intrinsic function."""

    def test_getazs_current_region(self):
        """GetAZs for current region."""
        g = GetAZs()
        assert g.to_dict() == {"Fn::GetAZs": ""}

    def test_getazs_specific_region(self):
        """GetAZs for specific region."""
        g = GetAZs("us-west-2")
        assert g.to_dict() == {"Fn::GetAZs": "us-west-2"}


class TestImportValue:
    """Tests for ImportValue intrinsic function."""

    def test_importvalue(self):
        """ImportValue exports from other stack."""
        i = ImportValue("SharedVPC-VpcId")
        assert i.to_dict() == {"Fn::ImportValue": "SharedVPC-VpcId"}


class TestFindInMap:
    """Tests for FindInMap intrinsic function."""

    def test_findinmap(self):
        """FindInMap looks up value."""
        f = FindInMap("RegionMap", Ref("AWS::Region"), "AMI")
        result = f.to_dict()
        assert result["Fn::FindInMap"][0] == "RegionMap"
        assert result["Fn::FindInMap"][1] == {"Ref": "AWS::Region"}
        assert result["Fn::FindInMap"][2] == "AMI"


class TestCidr:
    """Tests for Cidr intrinsic function."""

    def test_cidr(self):
        """Cidr generates IP ranges."""
        c = Cidr("10.0.0.0/16", 6, 8)
        assert c.to_dict() == {"Fn::Cidr": ["10.0.0.0/16", 6, 8]}


class TestSplit:
    """Tests for Split intrinsic function."""

    def test_split(self):
        """Split divides string."""
        s = Split(",", "a,b,c")
        assert s.to_dict() == {"Fn::Split": [",", "a,b,c"]}


class TestPseudoParameters:
    """Tests for pseudo-parameters."""

    def test_aws_account_id(self):
        """AWS::AccountId pseudo-parameter."""
        assert AWS_ACCOUNT_ID.to_dict() == {"Ref": "AWS::AccountId"}

    def test_aws_notification_arns(self):
        """AWS::NotificationARNs pseudo-parameter."""
        from wetwire_aws import AWS_NOTIFICATION_ARNS

        assert AWS_NOTIFICATION_ARNS.to_dict() == {"Ref": "AWS::NotificationARNs"}

    def test_aws_region(self):
        """AWS::Region pseudo-parameter."""
        assert AWS_REGION.to_dict() == {"Ref": "AWS::Region"}

    def test_aws_stack_id(self):
        """AWS::StackId pseudo-parameter."""
        assert AWS_STACK_ID.to_dict() == {"Ref": "AWS::StackId"}

    def test_aws_stack_name(self):
        """AWS::StackName pseudo-parameter."""
        assert AWS_STACK_NAME.to_dict() == {"Ref": "AWS::StackName"}

    def test_aws_partition(self):
        """AWS::Partition pseudo-parameter."""
        assert AWS_PARTITION.to_dict() == {"Ref": "AWS::Partition"}

    def test_aws_url_suffix(self):
        """AWS::URLSuffix pseudo-parameter."""
        assert AWS_URL_SUFFIX.to_dict() == {"Ref": "AWS::URLSuffix"}

    def test_aws_no_value(self):
        """AWS::NoValue pseudo-parameter."""
        assert AWS_NO_VALUE.to_dict() == {"Ref": "AWS::NoValue"}


class TestNestedIntrinsics:
    """Tests for nested intrinsic functions."""

    def test_sub_with_getatt(self):
        """Sub containing GetAtt."""
        s = Sub(
            "arn:aws:sqs:${AWS::Region}:${AWS::AccountId}:${QueueName}",
            {"QueueName": GetAtt("MyQueue", "QueueName")},
        )
        result = s.to_dict()
        assert result["Fn::Sub"][1]["QueueName"] == {
            "Fn::GetAtt": ["MyQueue", "QueueName"]
        }

    def test_join_with_if(self):
        """Join containing If."""
        j = Join(
            "-",
            [
                "prefix",
                If("IsProd", "prod", "dev"),
                "suffix",
            ],
        )
        result = j.to_dict()
        assert result["Fn::Join"][1][1] == {"Fn::If": ["IsProd", "prod", "dev"]}

    def test_select_with_getazs(self):
        """Select from GetAZs."""
        s = Select(0, GetAZs())
        result = s.to_dict()
        assert result["Fn::Select"][1] == {"Fn::GetAZs": ""}
