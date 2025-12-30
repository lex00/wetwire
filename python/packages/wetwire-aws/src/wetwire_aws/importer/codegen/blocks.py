"""Block mode PropertyType wrapper generation.

Block mode generates separate wrapper classes for nested PropertyType
structures instead of inline dicts. This produces more readable
code for complex nested properties.

For example, instead of:
    bucket_encryption = {'ServerSideEncryptionConfiguration': [...]}

Block mode generates:
    class MyBucketBucketEncryption:
        resource: s3.bucket.BucketEncryption
        server_side_encryption_configuration = [MyBucketServerSideEncryptionRule]

    class MyBucket:
        resource: s3.Bucket
        bucket_encryption = MyBucketBucketEncryption

Classes with `resource:` annotations are auto-decorated by setup_resources().

Key function: property_value_to_python_block()
"""

from __future__ import annotations

import datetime
import re
from typing import TYPE_CHECKING, Any

from wetwire_aws.importer.ir import IRIntrinsic

from .context import AnnotatedValue
from .helpers import (
    extract_class_from_type_hint,
    resolve_property_type,
)
from .values import (
    escape_string,
    intrinsic_to_python,
    value_to_python,
)

if TYPE_CHECKING:
    from .context import CodegenContext


# =============================================================================
# Block Mode Value Conversion
# =============================================================================


def property_value_to_python_block(
    value: Any,
    parent_logical_id: str,
    property_path: str,
    expected_type: str | None,
    expected_module: str | None,
    ctx: CodegenContext,
) -> str | AnnotatedValue:
    """Convert a property value to Python code in block mode.

    For PropertyTypes: generates separate wrapper class, returns class name.
    For primitives/enums: returns literal value.
    For lists of PropertyTypes: returns [WrapperClassName].

    Args:
        value: The value to convert
        parent_logical_id: Logical ID of the parent resource (e.g., "MyBucket")
        property_path: Dot-separated path for naming (e.g., "bucket_encryption")
        expected_type: Expected type from PropertyType field (e.g., "BucketEncryption")
        expected_module: Module hint from parent resource (e.g., "s3")
        ctx: Code generation context

    Returns:
        Python code string or AnnotatedValue for type-annotated fields.
    """
    if isinstance(value, IRIntrinsic):
        return intrinsic_to_python(value, ctx)

    if value is None:
        return "None"

    if isinstance(value, bool):
        return "True" if value else "False"

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, str):
        # TODO: Add enum conversion support
        return escape_string(value)

    if isinstance(value, list):
        return _convert_list_block(
            value, parent_logical_id, property_path, expected_type, expected_module, ctx
        )

    if isinstance(value, dict):
        return _convert_dict_block(
            value, parent_logical_id, property_path, expected_type, expected_module, ctx
        )

    return repr(value)


def _convert_list_block(
    value: list[Any],
    parent_logical_id: str,
    property_path: str,
    expected_type: str | None,
    expected_module: str | None,
    ctx: CodegenContext,
) -> str:
    """Convert a list value in block mode."""
    if not value:
        return "[]"

    # Extract inner type from list[...] annotation
    inner_class = None
    if expected_type:
        list_match = re.match(r".*list\[(\w+)\].*", expected_type, re.IGNORECASE)
        if list_match:
            inner_class = list_match.group(1)

    # Convert each item
    items = []
    for i, item in enumerate(value):
        item_result = property_value_to_python_block(
            item,
            parent_logical_id,
            f"{property_path}.{i}",
            f"Optional[{inner_class}]" if inner_class else expected_type,
            expected_module,
            ctx,
        )
        # AnnotatedValue is only for top-level properties, not inside lists
        if isinstance(item_result, AnnotatedValue):
            item_str = item_result.value
        else:
            item_str = item_result
        items.append(item_str)

    if len(items) == 1:
        return f"[{items[0]}]"
    return "[" + ", ".join(items) + "]"


def _convert_dict_block(
    value: dict[str, Any],
    parent_logical_id: str,
    property_path: str,
    expected_type: str | None,
    expected_module: str | None,
    ctx: CodegenContext,
) -> str:
    """Convert a dict value in block mode."""
    # Handle policy documents specially
    if _is_policy_document(value):
        return _generate_policy_document_wrapper_block(
            value, parent_logical_id, property_path, ctx
        )

    # Try to match to PropertyType
    expected_class = extract_class_from_type_hint(expected_type)
    cf_keys = set(value.keys())

    resolved = resolve_property_type(
        expected_class, expected_module, cf_keys, module_hint=expected_module
    )

    if resolved:
        pt_module, pt_class, pt_info = resolved
        class_name = generate_property_type_wrapper(
            value,
            parent_logical_id,
            property_path,
            pt_module,
            pt_class,
            pt_info,
            ctx,
        )
        return class_name

    # Fall back to dict literal
    return value_to_python(value, ctx, indent=1)


# =============================================================================
# PropertyType Wrapper Generation
# =============================================================================


def generate_property_type_wrapper(
    value: dict[str, Any],
    parent_logical_id: str,
    property_path: str,
    pt_module: str,
    pt_class: str,
    pt_info: dict[str, Any],
    ctx: CodegenContext,
) -> str:
    """Generate a wrapper class for a PropertyType value.

    Returns the generated class name.
    """
    # Mark that we're in a PropertyType wrapper - all resource refs should use
    # forward reference (string) syntax since wrappers appear before resource classes
    old_in_wrapper = ctx.in_property_type_wrapper
    ctx.in_property_type_wrapper = True

    try:
        return _generate_property_type_wrapper_impl(
            value, parent_logical_id, property_path, pt_module, pt_class, pt_info, ctx
        )
    finally:
        ctx.in_property_type_wrapper = old_in_wrapper


def _generate_property_type_wrapper_impl(
    value: dict[str, Any],
    parent_logical_id: str,
    property_path: str,
    pt_module: str,
    pt_class: str,
    pt_info: dict[str, Any],
    ctx: CodegenContext,
) -> str:
    """Internal implementation of generate_property_type_wrapper."""
    # Generate class name: {ParentLogicalId}{PropertyTypeName}
    class_name = f"{parent_logical_id}{pt_class}"

    # Handle name collisions by appending index
    if class_name in ctx.generated_classes:
        i = 1
        while f"{class_name}{i}" in ctx.generated_classes:
            i += 1
        class_name = f"{class_name}{i}"

    ctx.generated_classes.add(class_name)

    cf_to_python = pt_info["cf_to_python"]
    field_types = pt_info["field_types"]

    lines = []

    # Always use qualified module path: resource: s3.bucket.BucketEncryption
    base_module = pt_module.split(".")[0]
    ctx.add_import("wetwire_aws.resources", base_module)
    lines.append(f"    resource: {pt_module}.{pt_class}")

    # Build case-insensitive lookup for CF keys
    cf_to_python_lower = {k.lower(): v for k, v in cf_to_python.items()}

    # Convert each field
    for cf_key, val in value.items():
        python_field = None

        # Try direct lookup
        if cf_key in cf_to_python:
            python_field = cf_to_python[cf_key]
        # Try case-insensitive lookup (handles acronym variations like TTL/Ttl)
        elif cf_key.lower() in cf_to_python_lower:
            python_field = cf_to_python_lower[cf_key.lower()]
        else:
            # CF names often use acronyms (SSEAlgorithm, VPCId) that don't match
            # standard PascalCase. Try snake_case conversion of the CF key.
            from wetwire_aws.naming import to_snake_case

            candidate = to_snake_case(cf_key)
            if candidate in field_types:
                python_field = candidate

        if python_field:
            field_type = field_types.get(python_field)

            # Recursively handle nested PropertyTypes
            val_result = property_value_to_python_block(
                val,
                parent_logical_id,
                f"{property_path}.{python_field}",
                field_type,
                pt_module,
                ctx,
            )
            # Handle annotation-based refs for top-level properties
            if isinstance(val_result, AnnotatedValue):
                lines.append(
                    f"    {python_field}: {val_result.annotation} = {val_result.value}"
                )
            else:
                lines.append(f"    {python_field} = {val_result}")
        else:
            # Unknown key - include as comment
            val_str = value_to_python(val, ctx, indent=1)
            lines.append(f"    # Unknown CF key: {cf_key} = {val_str}")

    # Store class definition
    class_def = f"class {class_name}:\n" + "\n".join(lines)
    ctx.property_type_class_defs.append(class_def)

    # Return bare class name - no-parens pattern
    return class_name


# =============================================================================
# Policy Document/Statement Detection and Generation
# =============================================================================


def _is_policy_document(value: dict[str, Any]) -> bool:
    """Check if a dict looks like an IAM policy document."""
    return (
        isinstance(value, dict)
        and "Statement" in value
        and isinstance(value.get("Statement"), list)
    )


def _is_policy_statement(value: dict[str, Any]) -> bool:
    """Check if a dict looks like an IAM policy statement."""
    return (
        isinstance(value, dict)
        and "Effect" in value
        and value.get("Effect") in ("Allow", "Deny")
    )


def _generate_policy_statement_wrapper_block(
    stmt: dict[str, Any],
    parent_logical_id: str,
    property_path: str,
    stmt_index: int,
    ctx: CodegenContext,
) -> str:
    """Generate a wrapper class for a PolicyStatement.

    Returns the generated class name.
    """
    # Mark that we're in a PropertyType wrapper - all resource refs should use
    # forward reference (string) syntax since wrappers appear before resource classes
    old_in_wrapper = ctx.in_property_type_wrapper
    ctx.in_property_type_wrapper = True

    try:
        return _generate_policy_statement_wrapper_impl(
            stmt, parent_logical_id, property_path, stmt_index, ctx
        )
    finally:
        ctx.in_property_type_wrapper = old_in_wrapper


def _generate_policy_statement_wrapper_impl(
    stmt: dict[str, Any],
    parent_logical_id: str,
    property_path: str,
    stmt_index: int,
    ctx: CodegenContext,
) -> str:
    """Internal implementation of _generate_policy_statement_wrapper_block."""
    # Generate class name based on effect and index
    effect = stmt.get("Effect", "Allow")
    base_name = "Deny" if effect == "Deny" else "Allow"
    class_name = f"{parent_logical_id}{base_name}Statement{stmt_index}"

    # Handle name collisions
    if class_name in ctx.generated_classes:
        i = 1
        while f"{class_name}_{i}" in ctx.generated_classes:
            i += 1
        class_name = f"{class_name}_{i}"

    ctx.generated_classes.add(class_name)

    # Add imports
    if effect == "Deny":
        ctx.add_import("wetwire_aws", "DenyStatement")
        base_class = "DenyStatement"
    else:
        ctx.add_import("wetwire_aws", "PolicyStatement")
        base_class = "PolicyStatement"
    lines = []
    lines.append(f"    resource: {base_class}")

    # Map statement fields to PolicyStatement attributes
    if "Sid" in stmt:
        lines.append(f"    sid = {escape_string(stmt['Sid'])}")

    if "Principal" in stmt:
        principal_str = value_to_python(stmt["Principal"], ctx, indent=1)
        lines.append(f"    principal = {principal_str}")

    if "Action" in stmt:
        action_str = value_to_python(stmt["Action"], ctx, indent=1)
        lines.append(f"    action = {action_str}")

    if "Resource" in stmt:
        resource_str = value_to_python(stmt["Resource"], ctx, indent=1)
        lines.append(f"    resource_arn = {resource_str}")

    if "Condition" in stmt:
        condition_str = _condition_to_python(stmt["Condition"], ctx, indent=1)
        lines.append(f"    condition = {condition_str}")

    # Store class definition
    class_def = f"class {class_name}:\n" + "\n".join(lines)
    ctx.property_type_class_defs.append(class_def)

    # Return bare class name - no-parens pattern
    return class_name


def _generate_policy_document_wrapper_block(
    doc: dict[str, Any],
    parent_logical_id: str,
    property_path: str,
    ctx: CodegenContext,
) -> str:
    """Generate a wrapper class for a PolicyDocument.

    Returns the generated class name.
    """
    # Mark that we're in a PropertyType wrapper - all resource refs should use
    # forward reference (string) syntax since wrappers appear before resource classes
    old_in_wrapper = ctx.in_property_type_wrapper
    ctx.in_property_type_wrapper = True

    try:
        return _generate_policy_document_wrapper_impl(
            doc, parent_logical_id, property_path, ctx
        )
    finally:
        ctx.in_property_type_wrapper = old_in_wrapper


def _generate_policy_document_wrapper_impl(
    doc: dict[str, Any],
    parent_logical_id: str,
    property_path: str,
    ctx: CodegenContext,
) -> str:
    """Internal implementation of _generate_policy_document_wrapper_block."""
    # Generate class name
    # Convert property_path to PascalCase for class name suffix
    path_suffix = "".join(
        word.title() for word in property_path.replace(".", "_").split("_")
    )
    class_name = f"{parent_logical_id}{path_suffix}"

    # Handle name collisions
    if class_name in ctx.generated_classes:
        i = 1
        while f"{class_name}{i}" in ctx.generated_classes:
            i += 1
        class_name = f"{class_name}{i}"

    ctx.generated_classes.add(class_name)

    # Add imports
    ctx.add_import("wetwire_aws", "PolicyDocument")

    lines = []
    lines.append("    resource: PolicyDocument")

    # Handle version if not default
    version = doc.get("Version", "2012-10-17")
    if isinstance(version, (datetime.date, datetime.datetime)):
        version = version.strftime("%Y-%m-%d")
    if version != "2012-10-17":
        lines.append(f"    version = {escape_string(version)}")

    # Generate wrapper classes for each statement
    statements = doc.get("Statement", [])
    if statements:
        stmt_class_names = []
        for i, stmt in enumerate(statements):
            if isinstance(stmt, dict):
                stmt_class = _generate_policy_statement_wrapper_block(
                    stmt,
                    parent_logical_id,
                    f"{property_path}.statement.{i}",
                    i,
                    ctx,
                )
                stmt_class_names.append(stmt_class)
            else:
                # Handle non-dict statements (intrinsics, etc.)
                stmt_str = value_to_python(stmt, ctx, indent=1)
                stmt_class_names.append(stmt_str)

        if len(stmt_class_names) == 1:
            lines.append(f"    statement = [{stmt_class_names[0]}]")
        else:
            lines.append(f"    statement = [{', '.join(stmt_class_names)}]")

    # Store class definition
    class_def = f"class {class_name}:\n" + "\n".join(lines)
    ctx.property_type_class_defs.append(class_def)

    # Return bare class name - no-parens pattern
    return class_name


# =============================================================================
# Condition Operator Mapping
# =============================================================================

CONDITION_OPERATOR_MAP: dict[str, str] = {
    "StringEquals": "STRING_EQUALS",
    "StringNotEquals": "STRING_NOT_EQUALS",
    "StringEqualsIgnoreCase": "STRING_EQUALS_IGNORE_CASE",
    "StringNotEqualsIgnoreCase": "STRING_NOT_EQUALS_IGNORE_CASE",
    "StringLike": "STRING_LIKE",
    "StringNotLike": "STRING_NOT_LIKE",
    "NumericEquals": "NUMERIC_EQUALS",
    "NumericNotEquals": "NUMERIC_NOT_EQUALS",
    "NumericLessThan": "NUMERIC_LESS_THAN",
    "NumericLessThanEquals": "NUMERIC_LESS_THAN_EQUALS",
    "NumericGreaterThan": "NUMERIC_GREATER_THAN",
    "NumericGreaterThanEquals": "NUMERIC_GREATER_THAN_EQUALS",
    "DateEquals": "DATE_EQUALS",
    "DateNotEquals": "DATE_NOT_EQUALS",
    "DateLessThan": "DATE_LESS_THAN",
    "DateLessThanEquals": "DATE_LESS_THAN_EQUALS",
    "DateGreaterThan": "DATE_GREATER_THAN",
    "DateGreaterThanEquals": "DATE_GREATER_THAN_EQUALS",
    "Bool": "BOOL",
    "IpAddress": "IP_ADDRESS",
    "NotIpAddress": "NOT_IP_ADDRESS",
    "ArnEquals": "ARN_EQUALS",
    "ArnNotEquals": "ARN_NOT_EQUALS",
    "ArnLike": "ARN_LIKE",
    "ArnNotLike": "ARN_NOT_LIKE",
    "Null": "NULL",
}


def _condition_to_python(
    condition: dict[str, Any], ctx: CodegenContext, indent: int = 0
) -> str:
    """Convert a policy condition dict to Python code with operator constants.

    Transforms: {"Bool": {"key": "value"}} -> {BOOL: {"key": "value"}}
    """
    indent_str = "    " * indent

    if not condition:
        return "{}"

    items = []
    for operator, conditions in condition.items():
        # Use constant if available, otherwise string
        if operator in CONDITION_OPERATOR_MAP:
            const_name = CONDITION_OPERATOR_MAP[operator]
            ctx.add_import("wetwire_aws.constants", const_name)
            key_str = const_name
        else:
            key_str = escape_string(operator)

        val_str = value_to_python(conditions, ctx, indent + 1)
        items.append(f"{key_str}: {val_str}")

    inner = f",\n{indent_str}    ".join(items)
    return f"{{\n{indent_str}    {inner},\n{indent_str}}}"
