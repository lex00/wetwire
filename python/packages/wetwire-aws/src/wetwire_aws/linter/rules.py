"""Lint rules for wetwire-aws code.

This module defines the lint rules that detect patterns in user code that can
be improved. Each rule:

- Detects a specific anti-pattern (e.g., string literals instead of constants)
- Provides a clear message explaining the issue
- Suggests a better alternative with the exact replacement
- Specifies the imports needed for the fix

Rules:
    WAW001: Use parameter type constants instead of string literals
    WAW002: Use pseudo-parameter constants instead of Ref() with strings
    WAW003: Use enum constants instead of string literals
    WAW004: Use intrinsic function classes instead of raw dicts
    WAW005: Remove unnecessary .to_dict() calls on intrinsic functions

Example:
    >>> from wetwire_aws.linter.rules import get_all_rules, LintContext
    >>> import ast
    >>> source = 'type = "String"'
    >>> context = LintContext(source=source, tree=ast.parse(source))
    >>> for rule in get_all_rules():
    ...     issues = rule.check(context)
    ...     for issue in issues:
    ...         print(f"{issue.rule_id}: {issue.message}")
"""

from __future__ import annotations

import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass

from wetwire_aws.importer.codegen.helpers import (
    PARAMETER_TYPE_MAP,
    PSEUDO_PARAMETER_MAP,
)


@dataclass
class LintIssue:
    """A detected lint issue with fix information.

    Represents a single issue found by a lint rule, including all information
    needed to display the issue and optionally auto-fix it.

    Attributes:
        rule_id: The rule identifier (e.g., "WAW001").
        message: Human-readable description of the issue.
        line: Line number where the issue was found (1-indexed).
        column: Column number where the issue was found (0-indexed).
        original: The original code that should be replaced (empty for insertions).
        suggestion: The suggested replacement code (or line to insert).
        fix_imports: List of import statements needed for the fix.
        insert_after_line: If set, insert suggestion as new line after this line number.
            Line 0 means insert at the very beginning (after module docstring if present).
    """

    rule_id: str
    message: str
    line: int
    column: int
    original: str
    suggestion: str
    fix_imports: list[str]
    insert_after_line: int | None = None


@dataclass
class LintContext:
    """Context for linting, including source code and AST.

    Provides all the information a lint rule needs to analyze code.

    Attributes:
        source: The original source code as a string.
        tree: The parsed AST of the source code.
        filename: The filename for error messages (default: "<unknown>").
    """

    source: str
    tree: ast.AST
    filename: str = "<unknown>"


class LintRule(ABC):
    """Abstract base class for lint rules.

    Each lint rule must define a rule_id, description, and implement
    the check() method to detect issues.

    Attributes:
        rule_id: Unique identifier for the rule (e.g., "WAW001").
        description: Human-readable description of what the rule checks.
    """

    rule_id: str
    description: str

    @abstractmethod
    def check(self, context: LintContext) -> list[LintIssue]:
        """Check code for issues matching this rule.

        Args:
            context: The lint context containing source and AST.

        Returns:
            List of LintIssue objects for each detected issue.
        """
        pass


class StringShouldBeParameterType(LintRule):
    """Detect parameter types as string literals.

    Detects: type = "String", type = "Number"
    Suggests: type = STRING, type = NUMBER
    """

    rule_id = "WAW001"
    description = "Use parameter type constants instead of string literals"

    def check(self, context: LintContext) -> list[LintIssue]:
        issues = []

        for node in ast.walk(context.tree):
            # Look for assignments to 'type' attribute
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "type":
                        if isinstance(node.value, ast.Constant) and isinstance(
                            node.value.value, str
                        ):
                            type_str = node.value.value
                            if type_str in PARAMETER_TYPE_MAP:
                                constant_name = PARAMETER_TYPE_MAP[type_str]
                                import_stmt = f"from wetwire_aws.intrinsics import {constant_name}"

                                issues.append(
                                    LintIssue(
                                        rule_id=self.rule_id,
                                        message=f"Use {constant_name} instead of '{type_str}'",
                                        line=node.value.lineno,
                                        column=node.value.col_offset,
                                        original=f'"{type_str}"',
                                        suggestion=constant_name,
                                        fix_imports=[import_stmt],
                                    )
                                )

            # Also check keyword arguments in function/class calls
            if isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg == "type":
                        if isinstance(keyword.value, ast.Constant) and isinstance(
                            keyword.value.value, str
                        ):
                            type_str = keyword.value.value
                            if type_str in PARAMETER_TYPE_MAP:
                                constant_name = PARAMETER_TYPE_MAP[type_str]
                                import_stmt = f"from wetwire_aws.intrinsics import {constant_name}"

                                issues.append(
                                    LintIssue(
                                        rule_id=self.rule_id,
                                        message=f"Use {constant_name} instead of '{type_str}'",
                                        line=keyword.value.lineno,
                                        column=keyword.value.col_offset,
                                        original=f'"{type_str}"',
                                        suggestion=constant_name,
                                        fix_imports=[import_stmt],
                                    )
                                )

        return issues


class RefShouldBePseudoParameter(LintRule):
    """Detect Ref() calls with pseudo-parameters that should use constants.

    Detects: Ref("AWS::Region"), Ref("AWS::StackName")
    Suggests: AWS_REGION, AWS_STACK_NAME
    """

    rule_id = "WAW002"
    description = "Use pseudo-parameter constants instead of Ref() with string literals"

    def check(self, context: LintContext) -> list[LintIssue]:
        issues = []

        for node in ast.walk(context.tree):
            if isinstance(node, ast.Call):
                # Check if it's a Ref() call
                func = node.func
                is_ref = False
                if isinstance(func, ast.Name) and func.id == "Ref":
                    is_ref = True
                elif isinstance(func, ast.Attribute) and func.attr == "Ref":
                    is_ref = True

                if is_ref and node.args:
                    arg = node.args[0]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        pseudo_param = arg.value
                        if pseudo_param in PSEUDO_PARAMETER_MAP:
                            constant_name = PSEUDO_PARAMETER_MAP[pseudo_param]
                            import_stmt = (
                                f"from wetwire_aws.intrinsics import {constant_name}"
                            )

                            issues.append(
                                LintIssue(
                                    rule_id=self.rule_id,
                                    message=f"Use {constant_name} instead of Ref('{pseudo_param}')",
                                    line=node.lineno,
                                    column=node.col_offset,
                                    original=f'Ref("{pseudo_param}")',
                                    suggestion=constant_name,
                                    fix_imports=[import_stmt],
                                )
                            )

        return issues


class StringShouldBeEnum(LintRule):
    """Detect string literals that should be enum constants.

    This rule works by pattern matching known enum values in assignments,
    keyword arguments, and dict key-value pairs.

    Detects:
    - sse_algorithm = "AES256"
    - {'SSEAlgorithm': 'AES256'}
    - {'Status': 'Enabled'}

    Suggests:
    - sse_algorithm = ServerSideEncryption.AES256
    - {'SSEAlgorithm': ServerSideEncryption.AES256}
    - {'Status': BucketVersioningStatus.ENABLED}

    Note: This rule uses static analysis with known patterns.
    """

    rule_id = "WAW003"
    description = "Use enum constants instead of string literals"

    # Known enum patterns: field_name -> (enum_class, module, {value: constant_name})
    KNOWN_ENUMS: dict[str, tuple[str, str, dict[str, str]]] = {
        # S3 enums - snake_case keys
        "sse_algorithm": (
            "ServerSideEncryption",
            "wetwire_aws.resources.s3",
            {"AES256": "AES256", "aws:kms": "AWSKMS", "aws:kms:dsse": "AWSKMSDSSE"},
        ),
        "status": (
            "BucketVersioningStatus",
            "wetwire_aws.resources.s3",
            {"Enabled": "ENABLED", "Suspended": "SUSPENDED"},
        ),
        # DynamoDB enums
        "key_type": (
            "KeyType",
            "wetwire_aws.resources.dynamodb",
            {"HASH": "HASH", "RANGE": "RANGE"},
        ),
        "attribute_type": (
            "ScalarAttributeType",
            "wetwire_aws.resources.dynamodb",
            {"S": "S", "N": "N", "B": "B"},
        ),
        "billing_mode": (
            "BillingMode",
            "wetwire_aws.resources.dynamodb",
            {"PROVISIONED": "PROVISIONED", "PAY_PER_REQUEST": "PAY_PER_REQUEST"},
        ),
        # Lambda enums
        "runtime": (
            "Runtime",
            "wetwire_aws.resources.lambda_",
            {
                "python3.8": "PYTHON3_8",
                "python3.9": "PYTHON3_9",
                "python3.10": "PYTHON3_10",
                "python3.11": "PYTHON3_11",
                "python3.12": "PYTHON3_12",
                "nodejs18.x": "NODEJS18_X",
                "nodejs20.x": "NODEJS20_X",
            },
        ),
    }

    # CloudFormation PascalCase keys for dict literals
    KNOWN_DICT_KEYS: dict[str, tuple[str, str, dict[str, str]]] = {
        "SSEAlgorithm": (
            "ServerSideEncryption",
            "wetwire_aws.resources.s3",
            {"AES256": "AES256", "aws:kms": "AWSKMS", "aws:kms:dsse": "AWSKMSDSSE"},
        ),
        "Status": (
            "BucketVersioningStatus",
            "wetwire_aws.resources.s3",
            {"Enabled": "ENABLED", "Suspended": "SUSPENDED"},
        ),
        "KeyType": (
            "KeyType",
            "wetwire_aws.resources.dynamodb",
            {"HASH": "HASH", "RANGE": "RANGE"},
        ),
        "AttributeType": (
            "ScalarAttributeType",
            "wetwire_aws.resources.dynamodb",
            {"S": "S", "N": "N", "B": "B"},
        ),
        "Runtime": (
            "Runtime",
            "wetwire_aws.resources.lambda_",
            {
                "python3.8": "PYTHON3_8",
                "python3.9": "PYTHON3_9",
                "python3.10": "PYTHON3_10",
                "python3.11": "PYTHON3_11",
                "python3.12": "PYTHON3_12",
                "nodejs18.x": "NODEJS18_X",
                "nodejs20.x": "NODEJS20_X",
            },
        ),
    }

    def check(self, context: LintContext) -> list[LintIssue]:
        issues = []

        for node in ast.walk(context.tree):
            # Check assignments: field_name = "value"
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        field_name = target.id
                        if field_name in self.KNOWN_ENUMS:
                            if isinstance(node.value, ast.Constant) and isinstance(
                                node.value.value, str
                            ):
                                value = node.value.value
                                enum_class, module, value_map = self.KNOWN_ENUMS[
                                    field_name
                                ]
                                if value in value_map:
                                    const_name = value_map[value]
                                    suggestion = f"{enum_class}.{const_name}"
                                    import_stmt = f"from {module} import {enum_class}"

                                    issues.append(
                                        LintIssue(
                                            rule_id=self.rule_id,
                                            message=f"Use {suggestion} instead of '{value}'",
                                            line=node.value.lineno,
                                            column=node.value.col_offset,
                                            original=f'"{value}"',
                                            suggestion=suggestion,
                                            fix_imports=[import_stmt],
                                        )
                                    )

            # Check keyword arguments in function/class calls
            if isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg and keyword.arg in self.KNOWN_ENUMS:
                        if isinstance(keyword.value, ast.Constant) and isinstance(
                            keyword.value.value, str
                        ):
                            value = keyword.value.value
                            enum_class, module, value_map = self.KNOWN_ENUMS[
                                keyword.arg
                            ]
                            if value in value_map:
                                const_name = value_map[value]
                                suggestion = f"{enum_class}.{const_name}"
                                import_stmt = f"from {module} import {enum_class}"

                                issues.append(
                                    LintIssue(
                                        rule_id=self.rule_id,
                                        message=f"Use {suggestion} instead of '{value}'",
                                        line=keyword.value.lineno,
                                        column=keyword.value.col_offset,
                                        original=f'"{value}"',
                                        suggestion=suggestion,
                                        fix_imports=[import_stmt],
                                    )
                                )

            # Check dict literals: {'SSEAlgorithm': 'AES256'}
            if isinstance(node, ast.Dict):
                for key, val in zip(node.keys, node.values):
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        key_str = key.value
                        if key_str in self.KNOWN_DICT_KEYS:
                            if isinstance(val, ast.Constant) and isinstance(
                                val.value, str
                            ):
                                value = val.value
                                enum_class, module, value_map = self.KNOWN_DICT_KEYS[
                                    key_str
                                ]
                                if value in value_map:
                                    const_name = value_map[value]
                                    suggestion = f"{enum_class}.{const_name}"
                                    import_stmt = f"from {module} import {enum_class}"

                                    issues.append(
                                        LintIssue(
                                            rule_id=self.rule_id,
                                            message=f"Use {suggestion} instead of '{value}'",
                                            line=val.lineno,
                                            column=val.col_offset,
                                            original=f'"{value}"',
                                            suggestion=suggestion,
                                            fix_imports=[import_stmt],
                                        )
                                    )

        return issues


class DictShouldBeIntrinsic(LintRule):
    """Detect raw intrinsic function dicts that should use typed helpers.

    CloudFormation intrinsic functions like Ref, Sub, Select, Join, etc.
    should be expressed using the typed helpers from wetwire_aws.intrinsics
    rather than raw dict literals.

    Detects: {"Ref": "VpcId"}, {"Fn::Sub": "..."}, {"Fn::Select": [...]}
    Suggests: Ref("VpcId"), Sub("..."), Select(...)
    """

    rule_id = "WAW004"
    description = "Use intrinsic function classes instead of raw dicts"

    # Map CloudFormation intrinsic keys to Python function names
    INTRINSIC_MAP: dict[str, tuple[str, str]] = {
        "Ref": ("Ref", "wetwire_aws.intrinsics"),
        "Fn::Sub": ("Sub", "wetwire_aws.intrinsics"),
        "Fn::Select": ("Select", "wetwire_aws.intrinsics"),
        "Fn::Join": ("Join", "wetwire_aws.intrinsics"),
        "Fn::GetAZs": ("GetAZs", "wetwire_aws.intrinsics"),
        "Fn::GetAtt": ("GetAtt", "wetwire_aws.intrinsics"),
        "Fn::If": ("If", "wetwire_aws.intrinsics"),
        "Fn::Equals": ("Equals", "wetwire_aws.intrinsics"),
        "Fn::And": ("And", "wetwire_aws.intrinsics"),
        "Fn::Or": ("Or", "wetwire_aws.intrinsics"),
        "Fn::Not": ("Not", "wetwire_aws.intrinsics"),
        "Fn::Base64": ("Base64", "wetwire_aws.intrinsics"),
        "Fn::Split": ("Split", "wetwire_aws.intrinsics"),
        "Fn::ImportValue": ("ImportValue", "wetwire_aws.intrinsics"),
        "Fn::FindInMap": ("FindInMap", "wetwire_aws.intrinsics"),
        "Fn::Cidr": ("Cidr", "wetwire_aws.intrinsics"),
    }

    def check(self, context: LintContext) -> list[LintIssue]:
        issues = []

        # Check if file uses 'from . import *' pattern
        has_star_import = self._has_star_import(context.tree)

        for node in ast.walk(context.tree):
            # Look for single-key dict literals that match intrinsic patterns
            if isinstance(node, ast.Dict) and len(node.keys) == 1:
                key = node.keys[0]
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    key_str = key.value
                    if key_str in self.INTRINSIC_MAP:
                        func_name, module = self.INTRINSIC_MAP[key_str]

                        # Get the actual source text for the dict
                        original = ast.get_source_segment(context.source, node)

                        # Get the value and convert to source
                        value_node = node.values[0]
                        value_source = ast.get_source_segment(
                            context.source, value_node
                        )

                        # Build the replacement
                        if value_source:
                            if key_str == "Fn::GetAZs":
                                if value_source in ('""', "''", "AWS_REGION"):
                                    suggestion = f"{func_name}()"
                                else:
                                    suggestion = f"{func_name}({value_source})"
                            elif key_str in ("Fn::Select", "Fn::Join"):
                                if (
                                    isinstance(value_node, ast.List)
                                    and len(value_node.elts) >= 2
                                ):
                                    args = [
                                        ast.get_source_segment(context.source, elt)
                                        for elt in value_node.elts
                                    ]
                                    if all(args):
                                        suggestion = f"{func_name}({', '.join(args)})"
                                    else:
                                        suggestion = f"{func_name}({value_source})"
                                else:
                                    suggestion = f"{func_name}({value_source})"
                            else:
                                suggestion = f"{func_name}({value_source})"
                        else:
                            suggestion = f"{func_name}(...)"

                        fix_imports: list[str] = []
                        if not has_star_import:
                            fix_imports = [f"from {module} import {func_name}"]

                        if original:
                            issues.append(
                                LintIssue(
                                    rule_id=self.rule_id,
                                    message=f"Use {func_name}() instead of {{'{key_str}': ...}}",
                                    line=node.lineno,
                                    column=node.col_offset,
                                    original=original,
                                    suggestion=suggestion,
                                    fix_imports=fix_imports,
                                )
                            )

        return issues

    def _has_star_import(self, tree: ast.Module) -> bool:
        """Check if the module has a star import pattern."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module is None and node.level > 0:
                    for alias in node.names:
                        if alias.name == "*":
                            return True
        return False


class UnnecessaryToDict(LintRule):
    """Detect unnecessary .to_dict() calls on intrinsic function results.

    When using intrinsic functions like ref(), get_att(), Join(), etc.,
    calling .to_dict() is unnecessary because these functions return objects
    that serialize correctly when used directly.

    Detects: ref(MyResource).to_dict(), get_att(MyResource, "Arn").to_dict()
    Suggests: ref(MyResource), get_att(MyResource, "Arn")
    """

    rule_id = "WAW005"
    description = "Remove unnecessary .to_dict() calls on intrinsic functions"

    # Functions that return serializable intrinsic objects
    INTRINSIC_FUNCTIONS = {
        "ref",
        "get_att",
        "Ref",
        "GetAtt",
        "Sub",
        "Join",
        "Select",
        "If",
    }

    def check(self, context: LintContext) -> list[LintIssue]:
        issues = []

        for node in ast.walk(context.tree):
            # Look for method calls: something.to_dict()
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == "to_dict":
                    # Check if the object is a call to an intrinsic function
                    obj = node.func.value
                    if isinstance(obj, ast.Call):
                        func = obj.func
                        func_name = None
                        if isinstance(func, ast.Name):
                            func_name = func.id
                        elif isinstance(func, ast.Attribute):
                            func_name = func.attr

                        if func_name in self.INTRINSIC_FUNCTIONS:
                            issues.append(
                                LintIssue(
                                    rule_id=self.rule_id,
                                    message=f"Remove .to_dict() - {func_name}() returns a serializable object",
                                    line=node.lineno,
                                    column=node.col_offset,
                                    original=f"{func_name}(...).to_dict()",
                                    suggestion=f"{func_name}(...)",
                                    fix_imports=[],
                                )
                            )

        return issues


# All available rules
ALL_RULES: list[type[LintRule]] = [
    StringShouldBeParameterType,
    RefShouldBePseudoParameter,
    StringShouldBeEnum,
    DictShouldBeIntrinsic,
    UnnecessaryToDict,
]


def get_all_rules() -> list[LintRule]:
    """Get instances of all available lint rules.

    Returns:
        List of instantiated LintRule objects, one for each rule.
    """
    return [rule_cls() for rule_cls in ALL_RULES]
