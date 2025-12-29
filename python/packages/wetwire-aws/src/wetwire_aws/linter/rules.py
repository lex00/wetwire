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
    WAW006: Use no-parens references instead of ref()/get_att()
    WAW007: Use flat imports with module-qualified names instead of explicit resource imports
    WAW008: Remove verbose imports that setup_params/setup_resources handle
    WAW010: Split large files (>15 resources) into smaller category-based files
    WAW011: Use no-parens style for PropertyType wrappers (remove ())
    WAW012: Detect duplicate resource class names within a file

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

from wetwire_aws.constants import (
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

    Suggests (module-qualified, no imports needed):
    - sse_algorithm = s3.ServerSideEncryption.AES256
    - {'SSEAlgorithm': s3.ServerSideEncryption.AES256}
    - {'Status': s3.BucketVersioningStatus.ENABLED}

    Note: This rule uses static analysis with known patterns.
    The module-qualified form (e.g., s3.ServerSideEncryption) is preferred
    because the modules are available via `from . import *` in the package pattern.
    """

    rule_id = "WAW003"
    description = "Use enum constants instead of string literals"

    # Known enum patterns: field_name -> (enum_class, module_short, {value: constant_name})
    # module_short is the short module name (e.g., "s3", "lambda_") not the full path
    KNOWN_ENUMS: dict[str, tuple[str, str, dict[str, str]]] = {
        # S3 enums - snake_case keys
        "sse_algorithm": (
            "ServerSideEncryption",
            "s3",
            {"AES256": "AES256", "aws:kms": "AWSKMS", "aws:kms:dsse": "AWSKMSDSSE"},
        ),
        "status": (
            "BucketVersioningStatus",
            "s3",
            {"Enabled": "ENABLED", "Suspended": "SUSPENDED"},
        ),
        # DynamoDB enums
        "key_type": (
            "KeyType",
            "dynamodb",
            {"HASH": "HASH", "RANGE": "RANGE"},
        ),
        "attribute_type": (
            "ScalarAttributeType",
            "dynamodb",
            {"S": "S", "N": "N", "B": "B"},
        ),
        "billing_mode": (
            "BillingMode",
            "dynamodb",
            {"PROVISIONED": "PROVISIONED", "PAY_PER_REQUEST": "PAY_PER_REQUEST"},
        ),
        # Lambda enums
        "runtime": (
            "Runtime",
            "lambda_",
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
            "s3",
            {"AES256": "AES256", "aws:kms": "AWSKMS", "aws:kms:dsse": "AWSKMSDSSE"},
        ),
        "Status": (
            "BucketVersioningStatus",
            "s3",
            {"Enabled": "ENABLED", "Suspended": "SUSPENDED"},
        ),
        "KeyType": (
            "KeyType",
            "dynamodb",
            {"HASH": "HASH", "RANGE": "RANGE"},
        ),
        "AttributeType": (
            "ScalarAttributeType",
            "dynamodb",
            {"S": "S", "N": "N", "B": "B"},
        ),
        "Runtime": (
            "Runtime",
            "lambda_",
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
                                enum_class, module_short, value_map = self.KNOWN_ENUMS[
                                    field_name
                                ]
                                if value in value_map:
                                    const_name = value_map[value]
                                    # Use module-qualified form: s3.ServerSideEncryption.AES256
                                    suggestion = (
                                        f"{module_short}.{enum_class}.{const_name}"
                                    )

                                    issues.append(
                                        LintIssue(
                                            rule_id=self.rule_id,
                                            message=f"Use {suggestion} instead of '{value}'",
                                            line=node.value.lineno,
                                            column=node.value.col_offset,
                                            original=f'"{value}"',
                                            suggestion=suggestion,
                                            # No imports needed - modules available via from . import *
                                            fix_imports=[],
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
                            enum_class, module_short, value_map = self.KNOWN_ENUMS[
                                keyword.arg
                            ]
                            if value in value_map:
                                const_name = value_map[value]
                                # Use module-qualified form
                                suggestion = f"{module_short}.{enum_class}.{const_name}"

                                issues.append(
                                    LintIssue(
                                        rule_id=self.rule_id,
                                        message=f"Use {suggestion} instead of '{value}'",
                                        line=keyword.value.lineno,
                                        column=keyword.value.col_offset,
                                        original=f'"{value}"',
                                        suggestion=suggestion,
                                        fix_imports=[],
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
                                enum_class, module_short, value_map = (
                                    self.KNOWN_DICT_KEYS[key_str]
                                )
                                if value in value_map:
                                    const_name = value_map[value]
                                    # Use module-qualified form
                                    suggestion = (
                                        f"{module_short}.{enum_class}.{const_name}"
                                    )

                                    issues.append(
                                        LintIssue(
                                            rule_id=self.rule_id,
                                            message=f"Use {suggestion} instead of '{value}'",
                                            line=val.lineno,
                                            column=val.col_offset,
                                            original=f'"{value}"',
                                            suggestion=suggestion,
                                            fix_imports=[],
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


class RefShouldBeNoParens(LintRule):
    """Detect ref()/get_att() calls that should use no-parens style.

    The no-parens style is more declarative and readable. References to other
    resources should be expressed as bare class names, and attribute references
    as Class.Attribute.

    Detects:
    - ref(VPC) or ref("VPC")
    - get_att(MyRole, "Arn") or get_att("MyRole", "Arn")

    Suggests:
    - VPC
    - MyRole.Arn
    """

    rule_id = "WAW006"
    description = "Use no-parens references instead of ref()/get_att()"

    def check(self, context: LintContext) -> list[LintIssue]:
        issues = []

        for node in ast.walk(context.tree):
            if isinstance(node, ast.Call):
                func = node.func
                func_name = None

                if isinstance(func, ast.Name):
                    func_name = func.id
                elif isinstance(func, ast.Attribute):
                    func_name = func.attr

                # Check for ref() calls - only convert when target is a Name node
                # (already a class reference). String literals like ref("VPC") are
                # forward references and should not be converted to bare names.
                if func_name == "ref" and node.args:
                    arg = node.args[0]
                    # Only convert Name nodes (ref(VPC)), not string literals (ref("VPC"))
                    if isinstance(arg, ast.Name):
                        target = arg.id
                        original = ast.get_source_segment(context.source, node)
                        if original:
                            issues.append(
                                LintIssue(
                                    rule_id=self.rule_id,
                                    message=f"Use {target} instead of ref({target})",
                                    line=node.lineno,
                                    column=node.col_offset,
                                    original=original,
                                    suggestion=target,
                                    fix_imports=[],
                                )
                            )

                # Check for get_att() calls - only convert when target is a Name node
                # String-based forward references like get_att("VPC", "Arn") are needed
                # for classes defined later in the file (e.g., in PropertyType wrappers).
                if func_name == "get_att" and len(node.args) >= 2:
                    target_arg = node.args[0]
                    attr_arg = node.args[1]

                    # Only convert Name nodes, not string literals
                    if isinstance(target_arg, ast.Name):
                        target = target_arg.id
                        attr_name = self._extract_attr_name(attr_arg, context)

                        # Support both simple and nested attributes:
                        # - get_att(MyRole, "Arn") -> MyRole.Arn
                        # - get_att(MainDB, "Endpoint.Address") -> MainDB.Endpoint.Address
                        if attr_name:
                            original = ast.get_source_segment(context.source, node)
                            suggestion = f"{target}.{attr_name}"
                            if original:
                                issues.append(
                                    LintIssue(
                                        rule_id=self.rule_id,
                                        message=f"Use {suggestion} instead of get_att()",
                                        line=node.lineno,
                                        column=node.col_offset,
                                        original=original,
                                        suggestion=suggestion,
                                        fix_imports=[],
                                    )
                                )

        return issues

    def _extract_target(self, node: ast.expr) -> str | None:
        """Extract target class name from a ref/get_att argument.

        Handles both Name nodes (ref(VPC)) and string literals (ref("VPC")).
        """
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def _extract_attr_name(self, node: ast.expr, context: LintContext) -> str | None:
        """Extract attribute name from a get_att second argument.

        Handles string literals ("Arn") and constant references (ARN).
        """
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name):
            # It's a constant like ARN - get the source text
            return ast.get_source_segment(context.source, node)
        return None


class VerboseInitImports(LintRule):
    """Detect verbose imports in __init__.py that setup_params/setup_resources handle.

    When a package uses `setup_params()` and `setup_resources()`, they inject all
    needed AWS types. The __init__.py only needs:
        from wetwire_aws.loader import setup_params, setup_resources
        setup_params(globals())
        from .params import *
        setup_resources(__file__, __name__, globals())

    Detects:
    - from wetwire_aws import (...)  (multi-line import blocks)
    - from wetwire_aws.params import (...)  (should use setup_params instead)
    - from wetwire_aws.intrinsics import (...)  (should use setup_params instead)
    - __all__ = [...]  (explicit exports, not needed)

    Suggests:
    - Remove the verbose import block
    - Remove the __all__ definition
    """

    rule_id = "WAW008"
    description = "Remove verbose imports that setup_params/setup_resources handle"

    def check(self, context: LintContext) -> list[LintIssue]:
        issues = []

        # Only apply to files that use setup_resources (package __init__ files)
        if "setup_resources" not in context.source:
            return issues

        lines = context.source.splitlines(keepends=True)

        # Find and mark verbose import blocks for removal
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()

            # Detect verbose multi-line imports that setup_params handles:
            # - from wetwire_aws import (...)
            # - from wetwire_aws.params import (...)
            # - from wetwire_aws.intrinsics import (...)
            # But keep: from wetwire_aws.loader import setup_params, setup_resources
            verbose_prefixes = [
                "from wetwire_aws import (",
                "from wetwire_aws.params import (",
                "from wetwire_aws.intrinsics import (",
            ]

            if any(stripped.startswith(prefix) for prefix in verbose_prefixes):
                # Find the end of this import block
                start_line = i
                end_line = i
                paren_count = line.count("(") - line.count(")")
                while paren_count > 0 and end_line < len(lines) - 1:
                    end_line += 1
                    paren_count += lines[end_line].count("(")
                    paren_count -= lines[end_line].count(")")

                # Get the full multi-line import as original
                original_lines = lines[start_line : end_line + 1]
                original = "".join(original_lines).rstrip("\n")

                issues.append(
                    LintIssue(
                        rule_id=self.rule_id,
                        message="Remove verbose import; use setup_params() instead",
                        line=start_line + 1,  # 1-indexed
                        column=0,
                        original=original,
                        suggestion="",  # Remove entirely
                        fix_imports=[],
                    )
                )
                i = end_line + 1
                continue

            # Detect: __all__ = [
            if stripped.startswith("__all__") and "=" in stripped and "[" in stripped:
                # Find the end of this __all__ block
                start_line = i
                end_line = i
                bracket_count = line.count("[") - line.count("]")
                while bracket_count > 0 and end_line < len(lines) - 1:
                    end_line += 1
                    bracket_count += lines[end_line].count("[")
                    bracket_count -= lines[end_line].count("]")

                # Get the full multi-line __all__ as original
                original_lines = lines[start_line : end_line + 1]
                original = "".join(original_lines).rstrip("\n")

                issues.append(
                    LintIssue(
                        rule_id=self.rule_id,
                        message="Remove __all__; setup_resources() exports all classes automatically",
                        line=start_line + 1,  # 1-indexed
                        column=0,
                        original=original,
                        suggestion="",  # Remove entirely
                        fix_imports=[],
                    )
                )
                i = end_line + 1
                continue

            i += 1

        return issues


class ExplicitResourceImport(LintRule):
    """Detect explicit imports from wetwire_aws.resources that should use flat imports.

    Resource files should use `from . import *` and access types via module-qualified
    names (e.g., `lambda_.Runtime`, `s3.ServerSideEncryption`) rather than explicit
    imports. The `setup_resources()` function injects all service modules automatically.

    Detects:
    - from wetwire_aws.resources.lambda_ import Runtime
    - from wetwire_aws.resources.s3 import ServerSideEncryption
    - from wetwire_aws.resources import ec2, lambda_  (redundant in packages using setup_resources)

    Suggests:
    - Remove the import line
    - Qualify usages: Runtime.PYTHON3_12 -> lambda_.Runtime.PYTHON3_12
    """

    rule_id = "WAW007"
    description = "Use flat imports with module-qualified names instead of explicit resource imports"

    def check(self, context: LintContext) -> list[LintIssue]:
        issues = []

        # Check if this file uses setup_resources (indicating it's a package __init__)
        uses_setup_resources = "setup_resources" in context.source

        # First pass: collect all explicit resource imports
        # Maps imported name -> service module (e.g., "Runtime" -> "lambda_")
        imported_names: dict[str, str] = {}
        import_lines_to_remove: set[int] = set()

        for node in ast.walk(context.tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""

                # Check for imports from wetwire_aws.resources.* (e.g., lambda_, s3)
                if module.startswith("wetwire_aws.resources."):
                    # Extract the service module name (e.g., "lambda_", "s3")
                    parts = module.split(".")
                    if len(parts) >= 3:
                        service_module = parts[2]  # e.g., "lambda_", "s3"

                        for alias in node.names:
                            imported_name = alias.asname or alias.name
                            imported_names[imported_name] = service_module

                        # Mark this line for removal (only once per line)
                        if node.lineno not in import_lines_to_remove:
                            import_lines_to_remove.add(node.lineno)
                            original = ast.get_source_segment(context.source, node)
                            if original:
                                issues.append(
                                    LintIssue(
                                        rule_id=self.rule_id,
                                        message="Remove explicit resource import; use module-qualified names",
                                        line=node.lineno,
                                        column=node.col_offset,
                                        original=original,
                                        suggestion="",  # Remove the line
                                        fix_imports=[],
                                    )
                                )

                # Check for imports from wetwire_aws.resources (module imports)
                # These are redundant in packages using setup_resources()
                elif module == "wetwire_aws.resources" and uses_setup_resources:
                    if node.lineno not in import_lines_to_remove:
                        import_lines_to_remove.add(node.lineno)
                        original = ast.get_source_segment(context.source, node)
                        if original:
                            issues.append(
                                LintIssue(
                                    rule_id=self.rule_id,
                                    message="Remove redundant import; setup_resources() handles module injection",
                                    line=node.lineno,
                                    column=node.col_offset,
                                    original=original,
                                    suggestion="",  # Remove the line
                                    fix_imports=[],
                                )
                            )

        # Second pass: find usages of imported names and qualify them
        if imported_names:
            for node in ast.walk(context.tree):
                # Look for attribute access like Runtime.PYTHON3_12
                if isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name):
                        name = node.value.id
                        if name in imported_names:
                            service_module = imported_names[name]
                            # Get the full attribute access expression
                            original = ast.get_source_segment(context.source, node)
                            if original:
                                # Replace Name.attr with module.Name.attr
                                qualified = f"{service_module}.{original}"
                                issues.append(
                                    LintIssue(
                                        rule_id=self.rule_id,
                                        message=f"Use module-qualified name: {qualified}",
                                        line=node.lineno,
                                        column=node.col_offset,
                                        original=original,
                                        suggestion=qualified,
                                        fix_imports=[],
                                    )
                                )

        return issues


# NOTE: WAW009 (DependsOnShouldBeClassRef) was removed because converting
# depends_on from strings to class references causes forward reference issues.
# Resources may depend on classes defined later in the file, and Python class
# bodies are evaluated at definition time, before later classes exist.
# String literals like depends_on = ["VPCGatewayAttachment"] work reliably.


class FileTooLarge(LintRule):
    """Detect files with too many resources that should be split.

    Large files are harder to read, navigate, and maintain. Files with more
    than MAX_RESOURCES (default 15) resources should be split into smaller,
    focused files by category (storage, compute, network, security, etc.).

    The rule counts @wetwire_aws decorated classes in the file.

    Detects:
    - Files with > 15 @wetwire_aws decorated classes

    Suggests:
    - Split file into category-based files (storage.py, compute.py, etc.)
    """

    rule_id = "WAW010"
    description = "Split large files into smaller ones"
    MAX_RESOURCES = 15

    def check(self, context: LintContext) -> list[LintIssue]:
        issues = []

        # Count @wetwire_aws decorated classes
        resource_classes: list[tuple[str, int]] = []  # (name, line)

        for node in ast.walk(context.tree):
            if isinstance(node, ast.ClassDef):
                # Check if this class has @wetwire_aws decorator
                if self._has_wetwire_aws_decorator(node):
                    resource_classes.append((node.name, node.lineno))

        count = len(resource_classes)
        if count > self.MAX_RESOURCES:
            # Build a list of the resource names for the message
            names = [name for name, _ in resource_classes[:5]]
            if count > 5:
                names.append(f"... and {count - 5} more")

            issues.append(
                LintIssue(
                    rule_id=self.rule_id,
                    message=(
                        f"File has {count} resources (max {self.MAX_RESOURCES}). "
                        f"Consider splitting by category: storage.py, compute.py, "
                        f"network.py, security.py"
                    ),
                    line=1,  # File-level issue
                    column=0,
                    original="",  # No specific code to replace
                    suggestion=f"# Split {count} resources into multiple files",
                    fix_imports=[],
                )
            )

        return issues

    def _has_wetwire_aws_decorator(self, class_node: ast.ClassDef) -> bool:
        """Check if a class has the @wetwire_aws decorator."""
        for decorator in class_node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "wetwire_aws":
                return True
            if isinstance(decorator, ast.Attribute) and decorator.attr == "wetwire_aws":
                return True
        return False


class DuplicateResource(LintRule):
    """Detect duplicate @wetwire_aws class names within a file.

    CloudFormation logical resource names must be unique within a template.
    This rule catches duplicate class definitions early, at the Python level.

    Detects:
    - Two or more @wetwire_aws decorated classes with the same name in one file

    Note: Cross-file duplicate detection requires package-level analysis and
    is handled separately by setup_resources() at runtime.
    """

    rule_id = "WAW012"
    description = "Detect duplicate resource class names"

    def check(self, context: LintContext) -> list[LintIssue]:
        issues = []

        # Track class names and their locations
        class_locations: dict[str, list[tuple[int, int]]] = {}  # name -> [(line, col)]

        for node in ast.walk(context.tree):
            if isinstance(node, ast.ClassDef):
                # Check if this class has @wetwire_aws decorator
                if self._has_wetwire_aws_decorator(node):
                    name = node.name
                    if name not in class_locations:
                        class_locations[name] = []
                    class_locations[name].append((node.lineno, node.col_offset))

        # Report duplicates
        for name, locations in class_locations.items():
            if len(locations) > 1:
                # First occurrence is okay, report subsequent ones
                for line, col in locations[1:]:
                    first_line = locations[0][0]
                    issues.append(
                        LintIssue(
                            rule_id=self.rule_id,
                            message=(
                                f"Duplicate resource class '{name}' "
                                f"(first defined at line {first_line})"
                            ),
                            line=line,
                            column=col,
                            original=f"class {name}:",
                            suggestion=f"# DUPLICATE: class {name}:",
                            fix_imports=[],
                        )
                    )

        return issues

    def _has_wetwire_aws_decorator(self, class_node: ast.ClassDef) -> bool:
        """Check if a class has the @wetwire_aws decorator."""
        for decorator in class_node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "wetwire_aws":
                return True
            if isinstance(decorator, ast.Attribute) and decorator.attr == "wetwire_aws":
                return True
        return False


class PropertyTypeAsRef(LintRule):
    """Detect PropertyType wrapper instantiation that should use no-parens style.

    PropertyType wrapper classes should be referenced as bare class names, not
    instantiated with `()`. The serialization layer auto-instantiates these.

    This follows the no-parens declarative pattern where all wiring is expressed
    as class references rather than instance construction.

    Detects:
    - field = MyPropertyTypeWrapper()  (with empty parens)
    - statement = [AllowStatement()]  (with empty parens in list)

    Suggests:
    - field = MyPropertyTypeWrapper
    - statement = [AllowStatement]
    """

    rule_id = "WAW011"
    description = "Use no-parens style for PropertyType wrappers"

    # Known PropertyType base classes from wetwire_aws
    PROPERTY_TYPE_BASES = {
        "PolicyDocument",
        "PolicyStatement",
        "DenyStatement",
        "Tag",
        "PropertyType",
    }

    def check(self, context: LintContext) -> list[LintIssue]:
        issues = []

        # First pass: identify PropertyType wrapper classes in this file
        # A PropertyType wrapper has a `resource:` annotation pointing to a PropertyType
        property_type_wrappers: set[str] = set()

        for node in ast.walk(context.tree):
            if isinstance(node, ast.ClassDef):
                # Check for resource: annotation in class body
                for stmt in node.body:
                    if isinstance(stmt, ast.AnnAssign):
                        target = stmt.target
                        if isinstance(target, ast.Name) and target.id == "resource":
                            # Check what the annotation points to
                            if self._is_property_type_annotation(stmt.annotation):
                                property_type_wrappers.add(node.name)
                                break

        if not property_type_wrappers:
            return issues

        # Second pass: find usages of these wrappers with ()
        for node in ast.walk(context.tree):
            # Check direct assignments: field = WrapperClass()
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # Skip if target is 'resource' (the type annotation field)
                        if target.id == "resource":
                            continue

                        value = node.value
                        # Check for Call with no args: field = WrapperClass()
                        if isinstance(value, ast.Call):
                            if (
                                isinstance(value.func, ast.Name)
                                and value.func.id in property_type_wrappers
                                and not value.args
                                and not value.keywords
                            ):
                                original = ast.get_source_segment(context.source, value)
                                if original:
                                    class_name = value.func.id
                                    issues.append(
                                        LintIssue(
                                            rule_id=self.rule_id,
                                            message=f"Use no-parens style: {class_name}",
                                            line=value.lineno,
                                            column=value.col_offset,
                                            original=original,
                                            suggestion=class_name,
                                            fix_imports=[],
                                        )
                                    )

                        # Check lists: field = [WrapperClass(), WrapperClass2()]
                        elif isinstance(value, ast.List):
                            for elt in value.elts:
                                if isinstance(elt, ast.Call):
                                    if (
                                        isinstance(elt.func, ast.Name)
                                        and elt.func.id in property_type_wrappers
                                        and not elt.args
                                        and not elt.keywords
                                    ):
                                        original = ast.get_source_segment(
                                            context.source, elt
                                        )
                                        if original:
                                            class_name = elt.func.id
                                            issues.append(
                                                LintIssue(
                                                    rule_id=self.rule_id,
                                                    message=f"Use no-parens style: {class_name}",
                                                    line=elt.lineno,
                                                    column=elt.col_offset,
                                                    original=original,
                                                    suggestion=class_name,
                                                    fix_imports=[],
                                                )
                                            )

        return issues

    def _is_property_type_annotation(self, annotation: ast.expr) -> bool:
        """Check if an annotation refers to a PropertyType.

        Returns True for:
        - Name nodes like PolicyDocument, PolicyStatement, DenyStatement
        - Attribute nodes like s3.bucket.SomePropertyType (nested in a module)
        """
        if isinstance(annotation, ast.Name):
            return annotation.id in self.PROPERTY_TYPE_BASES

        if isinstance(annotation, ast.Attribute):
            # Check for nested property types like s3.bucket.BucketEncryption
            # or rds.db_proxy.TagFormat
            # These have at least one nested module (not just s3.Bucket which is a Resource)
            parts = self._get_attribute_parts(annotation)
            if len(parts) >= 3:
                # Format: module.submodule.ClassName (e.g., s3.bucket.BucketEncryption)
                # This is a nested PropertyType
                return True
            if len(parts) >= 2:
                # Check if the class name is in our known PropertyType bases
                class_name = parts[-1]
                return class_name in self.PROPERTY_TYPE_BASES

        return False

    def _get_attribute_parts(self, node: ast.expr) -> list[str]:
        """Extract parts from a nested Attribute node.

        For s3.bucket.BucketEncryption, returns ['s3', 'bucket', 'BucketEncryption'].
        """
        parts: list[str] = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        parts.reverse()
        return parts


# All available rules
ALL_RULES: list[type[LintRule]] = [
    StringShouldBeParameterType,
    RefShouldBePseudoParameter,
    StringShouldBeEnum,
    DictShouldBeIntrinsic,
    UnnecessaryToDict,
    RefShouldBeNoParens,
    ExplicitResourceImport,
    VerboseInitImports,
    FileTooLarge,
    PropertyTypeAsRef,
    DuplicateResource,
]


def get_all_rules() -> list[LintRule]:
    """Get instances of all available lint rules.

    Returns:
        List of instantiated LintRule objects, one for each rule.
    """
    return [rule_cls() for rule_cls in ALL_RULES]
