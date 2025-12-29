"""Tests for individual lint rules."""

import pytest

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
)


class TestStringShouldBeParameterType:
    """Tests for WAW001: parameter type string literals."""

    def test_detects_type_string(self):
        """Should detect type = 'String'."""
        code = '''
type = "String"
'''
        issues = lint_code(code, rules=[StringShouldBeParameterType()])
        assert len(issues) == 1
        assert issues[0].rule_id == "WAW001"
        assert "STRING" in issues[0].suggestion

    def test_detects_type_number(self):
        """Should detect type = 'Number'."""
        code = '''
type = "Number"
'''
        issues = lint_code(code, rules=[StringShouldBeParameterType()])
        assert len(issues) == 1
        assert "NUMBER" in issues[0].suggestion

    def test_detects_type_in_kwargs(self):
        """Should detect type in keyword arguments."""
        code = '''
param = Parameter(type="String", description="Test")
'''
        issues = lint_code(code, rules=[StringShouldBeParameterType()])
        assert len(issues) == 1
        assert "STRING" in issues[0].suggestion

    def test_ignores_non_parameter_types(self):
        """Should not flag arbitrary string assignments to type."""
        code = '''
type = "CustomType"
'''
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
        code = '''
region = Ref("AWS::Region")
'''
        issues = lint_code(code, rules=[RefShouldBePseudoParameter()])
        assert len(issues) == 1
        assert issues[0].rule_id == "WAW002"
        assert "AWS_REGION" in issues[0].suggestion

    def test_detects_aws_stack_name(self):
        """Should detect Ref('AWS::StackName')."""
        code = '''
stack_name = Ref("AWS::StackName")
'''
        issues = lint_code(code, rules=[RefShouldBePseudoParameter()])
        assert len(issues) == 1
        assert "AWS_STACK_NAME" in issues[0].suggestion

    def test_detects_aws_account_id(self):
        """Should detect Ref('AWS::AccountId')."""
        code = '''
account_id = Ref("AWS::AccountId")
'''
        issues = lint_code(code, rules=[RefShouldBePseudoParameter()])
        assert len(issues) == 1
        assert "AWS_ACCOUNT_ID" in issues[0].suggestion

    def test_detects_all_pseudo_parameters(self):
        """Should detect all AWS pseudo-parameters."""
        code = '''
region = Ref("AWS::Region")
stack = Ref("AWS::StackName")
account = Ref("AWS::AccountId")
partition = Ref("AWS::Partition")
'''
        issues = lint_code(code, rules=[RefShouldBePseudoParameter()])
        assert len(issues) == 4

    def test_ignores_regular_refs(self):
        """Should not flag Ref() with regular resource/parameter references."""
        code = '''
bucket_ref = Ref("MyBucket")
param_ref = Ref("Environment")
'''
        issues = lint_code(code, rules=[RefShouldBePseudoParameter()])
        assert len(issues) == 0

    def test_fix_replaces_ref(self):
        """Should replace Ref('AWS::Region') with AWS_REGION."""
        code = '''region = Ref("AWS::Region")'''
        fixed = fix_code(code, rules=[RefShouldBePseudoParameter()], add_imports=False)
        assert "AWS_REGION" in fixed
        assert 'Ref("AWS::Region")' not in fixed


class TestStringShouldBeEnum:
    """Tests for WAW003: string literals that should be enums."""

    def test_detects_sse_algorithm_aes256(self):
        """Should detect sse_algorithm = 'AES256' and suggest module-qualified name."""
        code = '''
sse_algorithm = "AES256"
'''
        issues = lint_code(code, rules=[StringShouldBeEnum()])
        assert len(issues) == 1
        assert issues[0].rule_id == "WAW003"
        assert issues[0].suggestion == "s3.ServerSideEncryption.AES256"

    def test_detects_sse_algorithm_aws_kms(self):
        """Should detect sse_algorithm = 'aws:kms' and suggest module-qualified name."""
        code = '''
sse_algorithm = "aws:kms"
'''
        issues = lint_code(code, rules=[StringShouldBeEnum()])
        assert len(issues) == 1
        assert issues[0].suggestion == "s3.ServerSideEncryption.AWSKMS"

    def test_detects_dynamodb_key_type(self):
        """Should detect DynamoDB key_type = 'HASH' and suggest module-qualified name."""
        code = '''
key_type = "HASH"
'''
        issues = lint_code(code, rules=[StringShouldBeEnum()])
        assert len(issues) == 1
        assert issues[0].suggestion == "dynamodb.KeyType.HASH"

    def test_detects_dynamodb_attribute_type(self):
        """Should detect DynamoDB attribute_type = 'S' and suggest module-qualified name."""
        code = '''
attribute_type = "S"
'''
        issues = lint_code(code, rules=[StringShouldBeEnum()])
        assert len(issues) == 1
        assert issues[0].suggestion == "dynamodb.ScalarAttributeType.S"

    def test_detects_enum_in_kwargs(self):
        """Should detect enum values in keyword arguments with module-qualified name."""
        code = '''
encryption = ServerSideEncryptionByDefault(sse_algorithm="AES256")
'''
        issues = lint_code(code, rules=[StringShouldBeEnum()])
        assert len(issues) == 1
        assert issues[0].suggestion == "s3.ServerSideEncryption.AES256"

    def test_ignores_unknown_field_names(self):
        """Should not flag unknown field names."""
        code = '''
unknown_field = "AES256"
'''
        issues = lint_code(code, rules=[StringShouldBeEnum()])
        assert len(issues) == 0

    def test_ignores_unknown_values(self):
        """Should not flag unknown values for known fields."""
        code = '''
sse_algorithm = "UNKNOWN_VALUE"
'''
        issues = lint_code(code, rules=[StringShouldBeEnum()])
        assert len(issues) == 0

    def test_fix_replaces_enum_value(self):
        """Should replace string with module-qualified enum constant."""
        code = '''sse_algorithm = "AES256"'''
        fixed = fix_code(code, rules=[StringShouldBeEnum()], add_imports=False)
        assert "s3.ServerSideEncryption.AES256" in fixed
        assert '"AES256"' not in fixed


class TestDictShouldBeIntrinsic:
    """Tests for WAW004: dict literals that should be intrinsic functions."""

    def test_detects_ref_dict(self):
        """Should detect {"Ref": "..."} dict pattern."""
        code = '''
value = {"Ref": "MyBucket"}
'''
        issues = lint_code(code, rules=[DictShouldBeIntrinsic()])
        assert len(issues) == 1
        assert issues[0].rule_id == "WAW004"
        assert "Ref(" in issues[0].suggestion

    def test_detects_fn_sub_dict(self):
        """Should detect {"Fn::Sub": "..."} dict pattern."""
        code = '''
value = {"Fn::Sub": "${AWS::Region}-bucket"}
'''
        issues = lint_code(code, rules=[DictShouldBeIntrinsic()])
        assert len(issues) == 1
        assert "Sub(" in issues[0].suggestion

    def test_detects_fn_getatt_dict(self):
        """Should detect {"Fn::GetAtt": "..."} dict pattern."""
        code = '''
value = {"Fn::GetAtt": "MyBucket.Arn"}
'''
        issues = lint_code(code, rules=[DictShouldBeIntrinsic()])
        assert len(issues) == 1
        assert "GetAtt(" in issues[0].suggestion

    def test_ignores_regular_dicts(self):
        """Should not flag regular dicts."""
        code = '''
data = {"Name": "value", "Value": 123}
'''
        issues = lint_code(code, rules=[DictShouldBeIntrinsic()])
        assert len(issues) == 0


class TestUnnecessaryToDict:
    """Tests for WAW005: unnecessary .to_dict() calls."""

    def test_detects_ref_to_dict(self):
        """Should detect ref().to_dict()."""
        code = '''
value = ref(MyBucket).to_dict()
'''
        issues = lint_code(code, rules=[UnnecessaryToDict()])
        assert len(issues) == 1
        assert issues[0].rule_id == "WAW005"
        assert "ref(" in issues[0].message

    def test_detects_get_att_to_dict(self):
        """Should detect get_att().to_dict()."""
        code = '''
value = get_att(MyBucket, "Arn").to_dict()
'''
        issues = lint_code(code, rules=[UnnecessaryToDict()])
        assert len(issues) == 1
        assert "get_att(" in issues[0].message

    def test_ignores_other_to_dict(self):
        """Should not flag .to_dict() on other objects."""
        code = '''
value = some_object.to_dict()
'''
        issues = lint_code(code, rules=[UnnecessaryToDict()])
        assert len(issues) == 0


class TestRefShouldBeNoParens:
    """Tests for WAW006: ref()/get_att() should use no-parens style."""

    def test_detects_ref_with_class_name(self):
        """Should detect ref(VPC) -> VPC."""
        code = '''
vpc_id = ref(VPC)
'''
        issues = lint_code(code, rules=[RefShouldBeNoParens()])
        assert len(issues) == 1
        assert issues[0].rule_id == "WAW006"
        assert issues[0].suggestion == "VPC"

    def test_ignores_ref_with_string(self):
        """Should ignore ref("VPC") - string literals are forward references."""
        code = '''
vpc_id = ref("VPC")
'''
        issues = lint_code(code, rules=[RefShouldBeNoParens()])
        # String literals are forward references and should not be flagged
        assert len(issues) == 0

    def test_detects_get_att_with_class_and_string(self):
        """Should detect get_att(MyRole, "Arn") -> MyRole.Arn."""
        code = '''
role_arn = get_att(MyRole, "Arn")
'''
        issues = lint_code(code, rules=[RefShouldBeNoParens()])
        assert len(issues) == 1
        assert issues[0].suggestion == "MyRole.Arn"

    def test_ignores_get_att_with_string_target(self):
        """Should ignore get_att("MyRole", "Arn") - string literals are forward references."""
        code = '''
role_arn = get_att("MyRole", "Arn")
'''
        issues = lint_code(code, rules=[RefShouldBeNoParens()])
        # String literals are forward references and should not be flagged
        assert len(issues) == 0

    def test_detects_get_att_with_constant(self):
        """Should detect get_att(MyRole, ARN) -> MyRole.ARN."""
        code = '''
role_arn = get_att(MyRole, ARN)
'''
        issues = lint_code(code, rules=[RefShouldBeNoParens()])
        assert len(issues) == 1
        assert issues[0].suggestion == "MyRole.ARN"

    def test_detects_multiple_refs(self):
        """Should detect multiple ref() calls."""
        code = '''
vpc_id = ref(VPC)
subnet_id = ref(Subnet)
'''
        issues = lint_code(code, rules=[RefShouldBeNoParens()])
        assert len(issues) == 2

    def test_fix_replaces_ref(self):
        """Should replace ref(VPC) with VPC."""
        code = '''vpc_id = ref(VPC)'''
        fixed = fix_code(code, rules=[RefShouldBeNoParens()], add_imports=False)
        assert "vpc_id = VPC" in fixed
        assert "ref(VPC)" not in fixed

    def test_fix_replaces_get_att(self):
        """Should replace get_att(MyRole, "Arn") with MyRole.Arn."""
        code = '''role_arn = get_att(MyRole, "Arn")'''
        fixed = fix_code(code, rules=[RefShouldBeNoParens()], add_imports=False)
        assert "role_arn = MyRole.Arn" in fixed
        assert "get_att(" not in fixed


class TestExplicitResourceImport:
    """Tests for WAW007: explicit resource imports."""

    def test_detects_lambda_runtime_import(self):
        """Should detect from wetwire_aws.resources.lambda_ import Runtime."""
        code = '''
from wetwire_aws.resources.lambda_ import Runtime
'''
        issues = lint_code(code, rules=[ExplicitResourceImport()])
        assert len(issues) == 1
        assert issues[0].rule_id == "WAW007"
        assert "Remove explicit resource import" in issues[0].message

    def test_detects_s3_enum_import(self):
        """Should detect from wetwire_aws.resources.s3 import ServerSideEncryption."""
        code = '''
from wetwire_aws.resources.s3 import ServerSideEncryption
'''
        issues = lint_code(code, rules=[ExplicitResourceImport()])
        assert len(issues) == 1
        assert "Remove explicit resource import" in issues[0].message

    def test_detects_multiple_imports_same_line(self):
        """Should detect one issue per import line (not per imported name)."""
        code = '''
from wetwire_aws.resources.lambda_ import Runtime, Architecture
'''
        issues = lint_code(code, rules=[ExplicitResourceImport()])
        # Now only 1 issue per import line
        assert len(issues) == 1

    def test_ignores_non_resource_imports(self):
        """Should not flag imports from wetwire_aws (not wetwire_aws.resources)."""
        code = '''
from wetwire_aws import wetwire_aws
from wetwire_aws.intrinsics import Sub
'''
        issues = lint_code(code, rules=[ExplicitResourceImport()])
        assert len(issues) == 0

    def test_fix_removes_import_line(self):
        """Should remove the explicit import line."""
        code = '''from wetwire_aws.resources.lambda_ import Runtime'''
        fixed = fix_code(code, rules=[ExplicitResourceImport()], add_imports=False)
        assert "from wetwire_aws.resources.lambda_" not in fixed

    def test_qualifies_usages_of_imported_names(self):
        """Should qualify usages like Runtime.PYTHON3_12 -> lambda_.Runtime.PYTHON3_12."""
        code = '''from wetwire_aws.resources.lambda_ import Runtime
runtime = Runtime.PYTHON3_12
'''
        issues = lint_code(code, rules=[ExplicitResourceImport()])
        # Should have 2 issues: 1 for import, 1 for usage
        assert len(issues) == 2
        # Filter for usage issues (ones that have a non-empty suggestion)
        usage_issues = [i for i in issues if i.suggestion and "lambda_.Runtime" in i.suggestion]
        assert len(usage_issues) == 1
        assert usage_issues[0].suggestion == "lambda_.Runtime.PYTHON3_12"

    def test_fix_qualifies_and_removes_import(self):
        """Should both remove import and qualify usages."""
        code = '''from wetwire_aws.resources.lambda_ import Runtime
runtime = Runtime.PYTHON3_12
'''
        fixed = fix_code(code, rules=[ExplicitResourceImport()], add_imports=False)
        assert "from wetwire_aws.resources.lambda_" not in fixed
        assert "lambda_.Runtime.PYTHON3_12" in fixed

    def test_detects_redundant_module_imports_in_init(self):
        """Should detect redundant module imports in __init__.py with setup_resources."""
        code = '''from wetwire_aws.loader import setup_resources
from wetwire_aws.resources import ec2, lambda_
setup_resources(__file__, __name__, globals())
'''
        issues = lint_code(code, rules=[ExplicitResourceImport()])
        assert len(issues) == 1
        assert "setup_resources()" in issues[0].message


class TestLintCodeIntegration:
    """Integration tests for lint_code with multiple rules."""

    def test_detects_multiple_issue_types(self):
        """Should detect issues from multiple rules."""
        code = '''
from wetwire_aws.intrinsics import Ref

type = "String"
region = Ref("AWS::Region")
sse_algorithm = "AES256"
'''
        issues = lint_code(code)
        # Should find: STRING, AWS_REGION, ServerSideEncryption.AES256
        assert len(issues) >= 3

        rule_ids = {issue.rule_id for issue in issues}
        assert "WAW001" in rule_ids  # Parameter type
        assert "WAW002" in rule_ids  # Pseudo parameter
        assert "WAW003" in rule_ids  # Enum

    def test_fix_code_fixes_all_issues(self):
        """Should fix all detected issues."""
        code = '''type = "String"
sse_algorithm = "AES256"
'''
        fixed = fix_code(code, add_imports=False)
        assert "STRING" in fixed
        assert "s3.ServerSideEncryption.AES256" in fixed
        assert '"String"' not in fixed
        assert '"AES256"' not in fixed

    def test_fix_code_no_imports_needed_for_module_qualified(self):
        """Module-qualified enums don't need imports (modules available via from . import *)."""
        code = '''sse_algorithm = "AES256"'''
        fixed = fix_code(code, add_imports=True)
        # No explicit import added because s3.ServerSideEncryption.AES256 uses module-qualified name
        assert "from wetwire_aws.resources.s3 import" not in fixed
        assert "s3.ServerSideEncryption.AES256" in fixed


class TestFixCodeImports:
    """Tests for import handling in fix_code."""

    def test_module_qualified_enums_no_imports_needed(self):
        """Module-qualified enums don't need explicit imports."""
        code = '''
sse_algorithm = "AES256"
status = "Enabled"
'''
        fixed = fix_code(code, add_imports=True, rules=[StringShouldBeEnum()])
        # Should NOT add explicit imports - modules available via from . import *
        assert "from wetwire_aws.resources.s3 import" not in fixed
        assert "s3.ServerSideEncryption.AES256" in fixed
        assert "s3.BucketVersioningStatus.ENABLED" in fixed

    def test_handles_syntax_errors_gracefully(self):
        """Should return original code for syntax errors."""
        code = '''this is not valid python'''
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
        code = '''from . import *

@wetwire_aws
class MyBucket:
    resource: s3.Bucket

@wetwire_aws
class MyRole:
    resource: iam.Role
'''
        issues = lint_code(code, rules=[FileTooLarge()])
        assert len(issues) == 0

    def test_ignores_non_wetwire_classes(self):
        """Should only count @wetwire_aws decorated classes."""
        code = '''from . import *

class HelperClass:
    pass

@dataclass
class DataClass:
    field: str

@wetwire_aws
class MyBucket:
    resource: s3.Bucket
'''
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
            ResourceInfo(f"Bucket{i}", "AWS::S3::Bucket", set())
            for i in range(20)
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
