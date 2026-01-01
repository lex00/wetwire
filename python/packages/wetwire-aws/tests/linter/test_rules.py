"""Tests for individual lint rules."""

import pytest
from unittest.mock import patch

from wetwire_aws.linter import (
    lint_code,
    fix_code,
    LintIssue,
    StringShouldBeParameterType,
    RefShouldBePseudoParameter,
    StringShouldBeEnum,
    DictShouldBeIntrinsic,
    UnnecessaryToDict,
    RefShouldBeNoParens,
    ExplicitResourceImport,
    FileTooLarge,
    DuplicateResource,
)


# Fixture to mock enum availability for WAW003 tests
@pytest.fixture
def mock_enum_available():
    """Mock _is_enum_available to always return True for testing."""
    with patch.object(StringShouldBeEnum, "_is_enum_available", return_value=True):
        yield


class TestStringShouldBeParameterType:
    """Tests for WAW001: parameter type string literals."""

    def test_detects_type_string(self):
        """Should detect type = 'String'."""
        code = """
type = "String"
"""
        issues = lint_code(code, rules=[StringShouldBeParameterType()])
        assert len(issues) == 1
        assert issues[0].rule_id == "WAW001"
        assert "STRING" in issues[0].suggestion

    def test_detects_type_number(self):
        """Should detect type = 'Number'."""
        code = """
type = "Number"
"""
        issues = lint_code(code, rules=[StringShouldBeParameterType()])
        assert len(issues) == 1
        assert "NUMBER" in issues[0].suggestion

    def test_detects_type_in_kwargs(self):
        """Should detect type in keyword arguments."""
        code = """
param = Parameter(type="String", description="Test")
"""
        issues = lint_code(code, rules=[StringShouldBeParameterType()])
        assert len(issues) == 1
        assert "STRING" in issues[0].suggestion

    def test_ignores_non_parameter_types(self):
        """Should not flag arbitrary string assignments to type."""
        code = """
type = "CustomType"
"""
        issues = lint_code(code, rules=[StringShouldBeParameterType()])
        assert len(issues) == 0

    def test_fix_replaces_string(self):
        """Should replace 'String' with STRING."""
        code = '''type = "String"'''
        fixed = fix_code(code, rules=[StringShouldBeParameterType()], add_imports=False)
        assert "STRING" in fixed
        assert '"String"' not in fixed


class TestRefShouldBePseudoParameter:
    """Tests for WAW002: Ref() with pseudo-parameters."""

    def test_detects_aws_region(self):
        """Should detect Ref('AWS::Region')."""
        code = """
region = Ref("AWS::Region")
"""
        issues = lint_code(code, rules=[RefShouldBePseudoParameter()])
        assert len(issues) == 1
        assert issues[0].rule_id == "WAW002"
        assert "AWS_REGION" in issues[0].suggestion

    def test_detects_aws_stack_name(self):
        """Should detect Ref('AWS::StackName')."""
        code = """
stack_name = Ref("AWS::StackName")
"""
        issues = lint_code(code, rules=[RefShouldBePseudoParameter()])
        assert len(issues) == 1
        assert "AWS_STACK_NAME" in issues[0].suggestion

    def test_detects_aws_account_id(self):
        """Should detect Ref('AWS::AccountId')."""
        code = """
account_id = Ref("AWS::AccountId")
"""
        issues = lint_code(code, rules=[RefShouldBePseudoParameter()])
        assert len(issues) == 1
        assert "AWS_ACCOUNT_ID" in issues[0].suggestion

    def test_detects_all_pseudo_parameters(self):
        """Should detect all AWS pseudo-parameters."""
        code = """
region = Ref("AWS::Region")
stack = Ref("AWS::StackName")
account = Ref("AWS::AccountId")
partition = Ref("AWS::Partition")
"""
        issues = lint_code(code, rules=[RefShouldBePseudoParameter()])
        assert len(issues) == 4

    def test_ignores_regular_refs(self):
        """Should not flag Ref() with regular resource/parameter references."""
        code = """
bucket_ref = Ref("MyBucket")
param_ref = Ref("Environment")
"""
        issues = lint_code(code, rules=[RefShouldBePseudoParameter()])
        assert len(issues) == 0

    def test_fix_replaces_ref(self):
        """Should replace Ref('AWS::Region') with AWS_REGION."""
        code = """region = Ref("AWS::Region")"""
        fixed = fix_code(code, rules=[RefShouldBePseudoParameter()], add_imports=False)
        assert "AWS_REGION" in fixed
        assert 'Ref("AWS::Region")' not in fixed


class TestStringShouldBeEnum:
    """Tests for WAW003: string literals that should be enums.

    These tests mock _is_enum_available to test pattern detection logic
    without requiring actual enum generation (which needs botocore).
    """

    def test_detects_sse_algorithm_aes256(self, mock_enum_available):
        """Should detect sse_algorithm = 'AES256' and suggest module-qualified name."""
        code = """
sse_algorithm = "AES256"
"""
        issues = lint_code(code, rules=[StringShouldBeEnum()])
        assert len(issues) == 1
        assert issues[0].rule_id == "WAW003"
        assert issues[0].suggestion == "s3.ServerSideEncryption.AES256"

    def test_detects_sse_algorithm_aws_kms(self, mock_enum_available):
        """Should detect sse_algorithm = 'aws:kms' and suggest module-qualified name."""
        code = """
sse_algorithm = "aws:kms"
"""
        issues = lint_code(code, rules=[StringShouldBeEnum()])
        assert len(issues) == 1
        assert issues[0].suggestion == "s3.ServerSideEncryption.AWSKMS"

    def test_detects_dynamodb_key_type(self, mock_enum_available):
        """Should detect DynamoDB key_type = 'HASH' and suggest module-qualified name."""
        code = """
key_type = "HASH"
"""
        issues = lint_code(code, rules=[StringShouldBeEnum()])
        assert len(issues) == 1
        assert issues[0].suggestion == "dynamodb.KeyType.HASH"

    def test_detects_dynamodb_attribute_type(self, mock_enum_available):
        """Should detect DynamoDB attribute_type = 'S' and suggest module-qualified name."""
        code = """
attribute_type = "S"
"""
        issues = lint_code(code, rules=[StringShouldBeEnum()])
        assert len(issues) == 1
        assert issues[0].suggestion == "dynamodb.ScalarAttributeType.S"

    def test_detects_enum_in_kwargs(self, mock_enum_available):
        """Should detect enum values in keyword arguments with module-qualified name."""
        code = """
encryption = ServerSideEncryptionByDefault(sse_algorithm="AES256")
"""
        issues = lint_code(code, rules=[StringShouldBeEnum()])
        assert len(issues) == 1
        assert issues[0].suggestion == "s3.ServerSideEncryption.AES256"

    def test_ignores_unknown_field_names(self):
        """Should not flag unknown field names."""
        code = """
unknown_field = "AES256"
"""
        issues = lint_code(code, rules=[StringShouldBeEnum()])
        assert len(issues) == 0

    def test_ignores_unknown_values(self):
        """Should not flag unknown values for known fields."""
        code = """
sse_algorithm = "UNKNOWN_VALUE"
"""
        issues = lint_code(code, rules=[StringShouldBeEnum()])
        assert len(issues) == 0

    def test_fix_replaces_enum_value(self, mock_enum_available):
        """Should replace string with module-qualified enum constant."""
        code = '''sse_algorithm = "AES256"'''
        fixed = fix_code(code, rules=[StringShouldBeEnum()], add_imports=False)
        assert "s3.ServerSideEncryption.AES256" in fixed
        assert '"AES256"' not in fixed


class TestDictShouldBeIntrinsic:
    """Tests for WAW004: dict literals that should be intrinsic functions."""

    def test_detects_ref_dict(self):
        """Should detect {"Ref": "..."} dict pattern."""
        code = """
value = {"Ref": "MyBucket"}
"""
        issues = lint_code(code, rules=[DictShouldBeIntrinsic()])
        assert len(issues) == 1
        assert issues[0].rule_id == "WAW004"
        assert "Ref(" in issues[0].suggestion

    def test_detects_fn_sub_dict(self):
        """Should detect {"Fn::Sub": "..."} dict pattern."""
        code = """
value = {"Fn::Sub": "${AWS::Region}-bucket"}
"""
        issues = lint_code(code, rules=[DictShouldBeIntrinsic()])
        assert len(issues) == 1
        assert "Sub(" in issues[0].suggestion

    def test_detects_fn_getatt_dict(self):
        """Should detect {"Fn::GetAtt": "..."} dict pattern."""
        code = """
value = {"Fn::GetAtt": "MyBucket.Arn"}
"""
        issues = lint_code(code, rules=[DictShouldBeIntrinsic()])
        assert len(issues) == 1
        assert "GetAtt(" in issues[0].suggestion

    def test_ignores_regular_dicts(self):
        """Should not flag regular dicts."""
        code = """
data = {"Name": "value", "Value": 123}
"""
        issues = lint_code(code, rules=[DictShouldBeIntrinsic()])
        assert len(issues) == 0


class TestUnnecessaryToDict:
    """Tests for WAW005: unnecessary .to_dict() calls."""

    def test_detects_ref_to_dict(self):
        """Should detect ref().to_dict()."""
        code = """
value = ref(MyBucket).to_dict()
"""
        issues = lint_code(code, rules=[UnnecessaryToDict()])
        assert len(issues) == 1
        assert issues[0].rule_id == "WAW005"
        assert "ref(" in issues[0].message

    def test_detects_get_att_to_dict(self):
        """Should detect get_att().to_dict()."""
        code = """
value = get_att(MyBucket, "Arn").to_dict()
"""
        issues = lint_code(code, rules=[UnnecessaryToDict()])
        assert len(issues) == 1
        assert "get_att(" in issues[0].message

    def test_ignores_other_to_dict(self):
        """Should not flag .to_dict() on other objects."""
        code = """
value = some_object.to_dict()
"""
        issues = lint_code(code, rules=[UnnecessaryToDict()])
        assert len(issues) == 0


class TestRefShouldBeNoParens:
    """Tests for WAW006: ref()/get_att() should use no-parens style."""

    def test_detects_ref_with_class_name(self):
        """Should detect ref(VPC) -> VPC."""
        code = """
vpc_id = ref(VPC)
"""
        issues = lint_code(code, rules=[RefShouldBeNoParens()])
        assert len(issues) == 1
        assert issues[0].rule_id == "WAW006"
        assert issues[0].suggestion == "VPC"

    def test_ignores_ref_with_string(self):
        """Should ignore ref("VPC") - string literals are forward references."""
        code = """
vpc_id = ref("VPC")
"""
        issues = lint_code(code, rules=[RefShouldBeNoParens()])
        # String literals are forward references and should not be flagged
        assert len(issues) == 0

    def test_detects_get_att_with_class_and_string(self):
        """Should detect get_att(MyRole, "Arn") -> MyRole.Arn."""
        code = """
role_arn = get_att(MyRole, "Arn")
"""
        issues = lint_code(code, rules=[RefShouldBeNoParens()])
        assert len(issues) == 1
        assert issues[0].suggestion == "MyRole.Arn"

    def test_ignores_get_att_with_string_target(self):
        """Should ignore get_att("MyRole", "Arn") - string literals are forward references."""
        code = """
role_arn = get_att("MyRole", "Arn")
"""
        issues = lint_code(code, rules=[RefShouldBeNoParens()])
        # String literals are forward references and should not be flagged
        assert len(issues) == 0

    def test_detects_get_att_with_constant(self):
        """Should detect get_att(MyRole, ARN) -> MyRole.ARN."""
        code = """
role_arn = get_att(MyRole, ARN)
"""
        issues = lint_code(code, rules=[RefShouldBeNoParens()])
        assert len(issues) == 1
        assert issues[0].suggestion == "MyRole.ARN"

    def test_detects_multiple_refs(self):
        """Should detect multiple ref() calls."""
        code = """
vpc_id = ref(VPC)
subnet_id = ref(Subnet)
"""
        issues = lint_code(code, rules=[RefShouldBeNoParens()])
        assert len(issues) == 2

    def test_fix_replaces_ref(self):
        """Should replace ref(VPC) with VPC."""
        code = """vpc_id = ref(VPC)"""
        fixed = fix_code(code, rules=[RefShouldBeNoParens()], add_imports=False)
        assert "vpc_id = VPC" in fixed
        assert "ref(VPC)" not in fixed

    def test_fix_replaces_get_att(self):
        """Should replace get_att(MyRole, "Arn") with MyRole.Arn."""
        code = """role_arn = get_att(MyRole, "Arn")"""
        fixed = fix_code(code, rules=[RefShouldBeNoParens()], add_imports=False)
        assert "role_arn = MyRole.Arn" in fixed
        assert "get_att(" not in fixed


class TestExplicitResourceImport:
    """Tests for WAW007: explicit resource imports."""

    def test_detects_lambda_runtime_import(self):
        """Should detect from wetwire_aws.resources.lambda_ import Runtime."""
        code = """
from wetwire_aws.resources.lambda_ import Runtime
"""
        issues = lint_code(code, rules=[ExplicitResourceImport()])
        assert len(issues) == 1
        assert issues[0].rule_id == "WAW007"
        assert "Remove explicit resource import" in issues[0].message

    def test_detects_s3_enum_import(self):
        """Should detect from wetwire_aws.resources.s3 import ServerSideEncryption."""
        code = """
from wetwire_aws.resources.s3 import ServerSideEncryption
"""
        issues = lint_code(code, rules=[ExplicitResourceImport()])
        assert len(issues) == 1
        assert "Remove explicit resource import" in issues[0].message

    def test_detects_multiple_imports_same_line(self):
        """Should detect one issue per import line (not per imported name)."""
        code = """
from wetwire_aws.resources.lambda_ import Runtime, Architecture
"""
        issues = lint_code(code, rules=[ExplicitResourceImport()])
        # Now only 1 issue per import line
        assert len(issues) == 1

    def test_ignores_non_resource_imports(self):
        """Should not flag imports from wetwire_aws (not wetwire_aws.resources)."""
        code = """
from wetwire_aws import wetwire_aws
from wetwire_aws.intrinsics import Sub
"""
        issues = lint_code(code, rules=[ExplicitResourceImport()])
        assert len(issues) == 0

    def test_fix_removes_import_line(self):
        """Should remove the explicit import line."""
        code = """from wetwire_aws.resources.lambda_ import Runtime"""
        fixed = fix_code(code, rules=[ExplicitResourceImport()], add_imports=False)
        assert "from wetwire_aws.resources.lambda_" not in fixed

    def test_qualifies_usages_of_imported_names(self):
        """Should qualify usages like Runtime.PYTHON3_12 -> lambda_.Runtime.PYTHON3_12."""
        code = """from wetwire_aws.resources.lambda_ import Runtime
runtime = Runtime.PYTHON3_12
"""
        issues = lint_code(code, rules=[ExplicitResourceImport()])
        # Should have 2 issues: 1 for import, 1 for usage
        assert len(issues) == 2
        # Filter for usage issues (ones that have a non-empty suggestion)
        usage_issues = [
            i for i in issues if i.suggestion and "lambda_.Runtime" in i.suggestion
        ]
        assert len(usage_issues) == 1
        assert usage_issues[0].suggestion == "lambda_.Runtime.PYTHON3_12"

    def test_fix_qualifies_and_removes_import(self):
        """Should both remove import and qualify usages."""
        code = """from wetwire_aws.resources.lambda_ import Runtime
runtime = Runtime.PYTHON3_12
"""
        fixed = fix_code(code, rules=[ExplicitResourceImport()], add_imports=False)
        assert "from wetwire_aws.resources.lambda_" not in fixed
        assert "lambda_.Runtime.PYTHON3_12" in fixed

    def test_detects_redundant_module_imports_in_init(self):
        """Should detect redundant module imports in __init__.py with setup_resources."""
        code = """from wetwire_aws.loader import setup_resources
from wetwire_aws.resources import ec2, lambda_
setup_resources(__file__, __name__, globals())
"""
        issues = lint_code(code, rules=[ExplicitResourceImport()])
        assert len(issues) == 1
        assert "setup_resources()" in issues[0].message


class TestLintCodeIntegration:
    """Integration tests for lint_code with multiple rules."""

    def test_detects_multiple_issue_types(self, mock_enum_available):
        """Should detect issues from multiple rules."""
        code = """
from wetwire_aws.intrinsics import Ref

type = "String"
region = Ref("AWS::Region")
sse_algorithm = "AES256"
"""
        issues = lint_code(code)
        # Should find: STRING, AWS_REGION, ServerSideEncryption.AES256
        assert len(issues) >= 3

        rule_ids = {issue.rule_id for issue in issues}
        assert "WAW001" in rule_ids  # Parameter type
        assert "WAW002" in rule_ids  # Pseudo parameter
        assert "WAW003" in rule_ids  # Enum

    def test_fix_code_fixes_all_issues(self, mock_enum_available):
        """Should fix all detected issues."""
        code = """type = "String"
sse_algorithm = "AES256"
"""
        fixed = fix_code(code, add_imports=False)
        assert "STRING" in fixed
        assert "s3.ServerSideEncryption.AES256" in fixed
        assert '"String"' not in fixed
        assert '"AES256"' not in fixed

    def test_fix_code_no_imports_needed_for_module_qualified(self, mock_enum_available):
        """Module-qualified enums don't need imports (modules available via from . import *)."""
        code = '''sse_algorithm = "AES256"'''
        fixed = fix_code(code, add_imports=True)
        # No explicit import added because s3.ServerSideEncryption.AES256 uses module-qualified name
        assert "from wetwire_aws.resources.s3 import" not in fixed
        assert "s3.ServerSideEncryption.AES256" in fixed


class TestFixCodeImports:
    """Tests for import handling in fix_code."""

    def test_module_qualified_enums_no_imports_needed(self, mock_enum_available):
        """Module-qualified enums don't need explicit imports."""
        code = """
sse_algorithm = "AES256"
status = "Enabled"
"""
        fixed = fix_code(code, add_imports=True, rules=[StringShouldBeEnum()])
        # Should NOT add explicit imports - modules available via from . import *
        assert "from wetwire_aws.resources.s3 import" not in fixed
        assert "s3.ServerSideEncryption.AES256" in fixed
        assert "s3.BucketVersioningStatus.ENABLED" in fixed

    def test_handles_syntax_errors_gracefully(self):
        """Should return original code for syntax errors."""
        code = """this is not valid python"""
        issues = lint_code(code)
        assert len(issues) == 0

        fixed = fix_code(code)
        # Should return unchanged since we can't fix invalid code
        assert "this is not valid python" in fixed


class TestFileTooLarge:
    """Tests for WAW010: file size limit."""

    def test_detects_file_over_limit(self):
        """Should detect files with > 15 @wetwire_aws classes."""
        # Generate code with 16 classes
        classes = "\n\n".join(
            f"@wetwire_aws\nclass Resource{i}:\n    resource: ec2.Instance"
            for i in range(16)
        )
        code = f"from . import *\n\n{classes}"

        issues = lint_code(code, rules=[FileTooLarge()])
        assert len(issues) == 1
        assert issues[0].rule_id == "WAW010"
        assert "16 resources" in issues[0].message
        assert "max 15" in issues[0].message

    def test_allows_file_at_limit(self):
        """Should not flag files with exactly 15 resources."""
        classes = "\n\n".join(
            f"@wetwire_aws\nclass Resource{i}:\n    resource: ec2.Instance"
            for i in range(15)
        )
        code = f"from . import *\n\n{classes}"

        issues = lint_code(code, rules=[FileTooLarge()])
        assert len(issues) == 0

    def test_allows_small_files(self):
        """Should not flag small files."""
        code = """from . import *

@wetwire_aws
class MyBucket:
    resource: s3.Bucket

@wetwire_aws
class MyRole:
    resource: iam.Role
"""
        issues = lint_code(code, rules=[FileTooLarge()])
        assert len(issues) == 0

    def test_ignores_non_wetwire_classes(self):
        """Should only count @wetwire_aws decorated classes."""
        code = """from . import *

class HelperClass:
    pass

@dataclass
class DataClass:
    field: str

@wetwire_aws
class MyBucket:
    resource: s3.Bucket
"""
        issues = lint_code(code, rules=[FileTooLarge()])
        assert len(issues) == 0


class TestSplittingUtilities:
    """Tests for file splitting utilities in linter/splitting.py."""

    def test_categorize_s3_as_storage(self):
        """S3 resources should categorize as storage."""
        from wetwire_aws.linter.splitting import categorize_resource_type

        assert categorize_resource_type("AWS::S3::Bucket") == "storage"

    def test_categorize_ec2_instance_as_compute(self):
        """EC2 Instance should categorize as compute."""
        from wetwire_aws.linter.splitting import categorize_resource_type

        assert categorize_resource_type("AWS::EC2::Instance") == "compute"

    def test_categorize_ec2_vpc_as_network(self):
        """EC2 VPC should categorize as network (not compute)."""
        from wetwire_aws.linter.splitting import categorize_resource_type

        assert categorize_resource_type("AWS::EC2::VPC") == "network"
        assert categorize_resource_type("AWS::EC2::Subnet") == "network"
        assert categorize_resource_type("AWS::EC2::SecurityGroup") == "network"

    def test_categorize_iam_as_security(self):
        """IAM resources should categorize as security."""
        from wetwire_aws.linter.splitting import categorize_resource_type

        assert categorize_resource_type("AWS::IAM::Role") == "security"

    def test_categorize_unknown_as_main(self):
        """Unknown resources should categorize as main."""
        from wetwire_aws.linter.splitting import categorize_resource_type

        assert categorize_resource_type("AWS::Unknown::Resource") == "main"
        assert categorize_resource_type("InvalidFormat") == "main"

    def test_is_ec2_network_type_core_types(self):
        """Core network types should be detected."""
        from wetwire_aws.linter.splitting import is_ec2_network_type

        assert is_ec2_network_type("VPC") is True
        assert is_ec2_network_type("Subnet") is True
        assert is_ec2_network_type("SecurityGroup") is True
        assert is_ec2_network_type("SecurityGroupIngress") is True
        assert is_ec2_network_type("SecurityGroupEgress") is True
        assert is_ec2_network_type("RouteTable") is True
        assert is_ec2_network_type("NetworkInterface") is True

    def test_is_ec2_network_type_compute_types(self):
        """Compute types should NOT be detected as network."""
        from wetwire_aws.linter.splitting import is_ec2_network_type

        assert is_ec2_network_type("Instance") is False
        assert is_ec2_network_type("LaunchTemplate") is False
        assert is_ec2_network_type("Volume") is False
        assert is_ec2_network_type("Snapshot") is False
        assert is_ec2_network_type("KeyPair") is False
        assert is_ec2_network_type("SpotFleet") is False

    def test_is_ec2_network_type_endpoint_types(self):
        """Endpoint types should be detected as network."""
        from wetwire_aws.linter.splitting import is_ec2_network_type

        assert is_ec2_network_type("VPCEndpoint") is True
        assert is_ec2_network_type("VPCEndpointService") is True
        assert is_ec2_network_type("ClientVpnEndpoint") is True

    def test_is_ec2_network_type_new_types(self):
        """Newly-added network types should be detected dynamically."""
        from wetwire_aws.linter.splitting import is_ec2_network_type

        # These were previously missing from the static list
        assert is_ec2_network_type("TransitGatewayRouteTable") is True
        assert is_ec2_network_type("TrafficMirrorSession") is True
        assert is_ec2_network_type("TrafficMirrorTarget") is True
        assert is_ec2_network_type("PrefixList") is True
        assert is_ec2_network_type("VerifiedAccessEndpoint") is True
        assert is_ec2_network_type("LocalGatewayRouteTable") is True

    def test_categorize_ec2_security_group_ingress(self):
        """SecurityGroupIngress should categorize as network via dynamic inference."""
        from wetwire_aws.linter.splitting import categorize_resource_type

        assert categorize_resource_type("AWS::EC2::SecurityGroupIngress") == "network"
        assert categorize_resource_type("AWS::EC2::SecurityGroupEgress") == "network"

    def test_suggest_file_splits_basic(self):
        """Test basic file splitting suggestion."""
        from wetwire_aws.linter.splitting import ResourceInfo, suggest_file_splits

        resources = [
            ResourceInfo("MyBucket", "AWS::S3::Bucket", set()),
            ResourceInfo("MyVPC", "AWS::EC2::VPC", set()),
            ResourceInfo("MyRole", "AWS::IAM::Role", set()),
        ]

        splits = suggest_file_splits(resources)

        assert "storage" in splits
        assert "MyBucket" in splits["storage"]
        assert "network" in splits
        assert "MyVPC" in splits["network"]
        assert "security" in splits
        assert "MyRole" in splits["security"]

    def test_suggest_file_splits_respects_max(self):
        """Test that file splits respect max_per_file."""
        from wetwire_aws.linter.splitting import ResourceInfo, suggest_file_splits

        # Create 20 S3 buckets
        resources = [
            ResourceInfo(f"Bucket{i}", "AWS::S3::Bucket", set()) for i in range(20)
        ]

        # With max 15, should split into storage1, storage2
        splits = suggest_file_splits(resources, max_per_file=15)

        assert "storage1" in splits or "storage2" in splits
        total_resources = sum(len(v) for v in splits.values())
        assert total_resources == 20

    def test_calculate_scc_weight(self):
        """Test SCC weight calculation."""
        from wetwire_aws.linter.splitting import (
            ResourceInfo,
            calculate_scc_weight,
        )

        resources = {
            "A": ResourceInfo("A", "AWS::S3::Bucket", {"B", "C"}),
            "B": ResourceInfo("B", "AWS::S3::Bucket", {"A"}),
            "C": ResourceInfo("C", "AWS::S3::Bucket", set()),
        }

        # A->B, B->A = 2 internal edges
        weight = calculate_scc_weight(["A", "B"], resources)
        assert weight == 2  # A depends on B, B depends on A


class TestPropertyTypeAsRef:
    """Tests for WAW011: PropertyType wrappers should use no-parens style."""

    def test_detects_policy_document_wrapper_with_parens(self):
        """Should detect PolicyDocument wrapper used with ()."""
        from wetwire_aws.linter.rules import PropertyTypeAsRef

        code = """
@wetwire_aws
class MyPolicyDoc:
    resource: PolicyDocument
    statement = []

@wetwire_aws
class MyRole:
    resource: iam.Role
    assume_role_policy_document = MyPolicyDoc()
"""
        issues = lint_code(code, rules=[PropertyTypeAsRef()])
        assert len(issues) == 1
        assert issues[0].rule_id == "WAW011"
        assert issues[0].suggestion == "MyPolicyDoc"

    def test_detects_policy_statement_wrapper_with_parens(self):
        """Should detect PolicyStatement wrapper used with ()."""
        from wetwire_aws.linter.rules import PropertyTypeAsRef

        code = """
@wetwire_aws
class AllowStatement:
    resource: PolicyStatement
    action = "sts:AssumeRole"

@wetwire_aws
class MyPolicyDoc:
    resource: PolicyDocument
    statement = [AllowStatement()]
"""
        issues = lint_code(code, rules=[PropertyTypeAsRef()])
        assert len(issues) == 1
        assert issues[0].suggestion == "AllowStatement"

    def test_detects_nested_property_type_wrapper_with_parens(self):
        """Should detect nested PropertyType wrapper (e.g., s3.Bucket.BucketEncryption) with ()."""
        from wetwire_aws.linter.rules import PropertyTypeAsRef

        code = """
@wetwire_aws
class MyBucketEncryption:
    resource: s3.Bucket.BucketEncryption
    sse_algorithm = "AES256"

@wetwire_aws
class MyBucket:
    resource: s3.Bucket
    bucket_encryption = MyBucketEncryption()
"""
        issues = lint_code(code, rules=[PropertyTypeAsRef()])
        assert len(issues) == 1
        assert issues[0].suggestion == "MyBucketEncryption"

    def test_ignores_resource_wrappers(self):
        """Should not flag resource wrappers (these are valid as class refs)."""
        from wetwire_aws.linter.rules import PropertyTypeAsRef

        code = """
@wetwire_aws
class MyVPC:
    resource: ec2.VPC
    cidr_block = "10.0.0.0/16"

@wetwire_aws
class MySubnet:
    resource: ec2.Subnet
    vpc_id = MyVPC
"""
        issues = lint_code(code, rules=[PropertyTypeAsRef()])
        assert len(issues) == 0

    def test_ignores_already_no_parens(self):
        """Should not flag PropertyType wrappers that already use no-parens style."""
        from wetwire_aws.linter.rules import PropertyTypeAsRef

        code = """
@wetwire_aws
class MyPolicyDoc:
    resource: PolicyDocument
    statement = []

@wetwire_aws
class MyRole:
    resource: iam.Role
    assume_role_policy_document = MyPolicyDoc
"""
        issues = lint_code(code, rules=[PropertyTypeAsRef()])
        assert len(issues) == 0

    def test_detects_multiple_in_list_with_parens(self):
        """Should detect multiple PropertyType wrappers with () in a list."""
        from wetwire_aws.linter.rules import PropertyTypeAsRef

        code = """
@wetwire_aws
class AllowStatement1:
    resource: PolicyStatement
    action = "s3:GetObject"

@wetwire_aws
class AllowStatement2:
    resource: PolicyStatement
    action = "s3:PutObject"

@wetwire_aws
class MyPolicyDoc:
    resource: PolicyDocument
    statement = [AllowStatement1(), AllowStatement2()]
"""
        issues = lint_code(code, rules=[PropertyTypeAsRef()])
        assert len(issues) == 2
        assert issues[0].suggestion == "AllowStatement1"
        assert issues[1].suggestion == "AllowStatement2"

    def test_fix_removes_parentheses(self):
        """Should fix by removing () from the wrapper."""
        from wetwire_aws.linter.rules import PropertyTypeAsRef

        code = """@wetwire_aws
class MyPolicyDoc:
    resource: PolicyDocument
    statement = []

@wetwire_aws
class MyRole:
    resource: iam.Role
    assume_role_policy_document = MyPolicyDoc()"""
        fixed = fix_code(code, rules=[PropertyTypeAsRef()], add_imports=False)
        assert (
            "assume_role_policy_document = MyPolicyDoc\n" in fixed
            or fixed.strip().endswith("assume_role_policy_document = MyPolicyDoc")
        )


class TestDuplicateResource:
    """Tests for WAW012: duplicate resource class names."""

    def test_detects_duplicate_class_names(self):
        """Should detect duplicate @wetwire_aws class names in same file."""
        code = """
@wetwire_aws
class MyBucket:
    resource: s3.Bucket
    bucket_name = "bucket-1"

@wetwire_aws
class MyBucket:
    resource: s3.Bucket
    bucket_name = "bucket-2"
"""
        issues = lint_code(code, rules=[DuplicateResource()])
        assert len(issues) == 1
        assert issues[0].rule_id == "WAW012"
        assert "Duplicate resource class 'MyBucket'" in issues[0].message
        assert "first defined at line" in issues[0].message

    def test_detects_multiple_duplicates(self):
        """Should detect all duplicate definitions."""
        code = """
@wetwire_aws
class MyBucket:
    resource: s3.Bucket

@wetwire_aws
class MyBucket:
    resource: s3.Bucket

@wetwire_aws
class MyBucket:
    resource: s3.Bucket
"""
        issues = lint_code(code, rules=[DuplicateResource()])
        assert len(issues) == 2  # Two duplicates (first is the original)

    def test_ignores_unique_classes(self):
        """Should not flag unique class names."""
        code = """
@wetwire_aws
class MyBucket:
    resource: s3.Bucket

@wetwire_aws
class MyVPC:
    resource: ec2.VPC

@wetwire_aws
class MyRole:
    resource: iam.Role
"""
        issues = lint_code(code, rules=[DuplicateResource()])
        assert len(issues) == 0

    def test_ignores_non_wetwire_classes(self):
        """Should not flag non-wetwire_aws classes with same name."""
        code = """
class MyBucket:
    pass

@wetwire_aws
class MyBucket:
    resource: s3.Bucket
"""
        issues = lint_code(code, rules=[DuplicateResource()])
        assert len(issues) == 0

    def test_reports_correct_line_numbers(self):
        """Should report correct line numbers for duplicate definitions."""
        code = """
@wetwire_aws
class MyBucket:
    resource: s3.Bucket

@wetwire_aws
class OtherResource:
    resource: ec2.VPC

@wetwire_aws
class MyBucket:
    resource: s3.Bucket
"""
        issues = lint_code(code, rules=[DuplicateResource()])
        assert len(issues) == 1
        assert issues[0].line == 11  # Line of second MyBucket definition
        assert "first defined at line 3" in issues[0].message
