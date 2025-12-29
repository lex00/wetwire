"""Value serialization to Python source code.

This module converts IR values (literals, lists, dicts, intrinsics) into
Python source code strings.

Policy documents are "flattened" into separate wrapper classes:
- Each Statement becomes a PolicyStatement wrapper class
- The PolicyDocument becomes a wrapper class referencing statements
- The original property references the PolicyDocument class by name
"""

from __future__ import annotations

import datetime
import re
from typing import TYPE_CHECKING, Any

from wetwire_aws.importer.ir import IntrinsicType, IRIntrinsic

from .context import AnnotatedValue
from .helpers import PSEUDO_PARAMETER_MAP, sanitize_class_name

if TYPE_CHECKING:
    from .context import CodegenContext


# =============================================================================
# String Escaping
# =============================================================================


def escape_string(s: str) -> str:
    """Escape a string for Python source code.

    Chooses appropriate quoting style: repr() for single-line strings,
    triple quotes for multi-line strings.
    """
    if "\n" in s:
        # Use triple quotes for multi-line
        if '"""' not in s:
            return f'"""{s}"""'
        if "'''" not in s:
            return f"'''{s}'''"
        return repr(s)
    return repr(s)


def escape_docstring(s: str) -> str:
    """Escape a string for use as a docstring."""
    if '"""' in s:
        escaped = s.replace('"""', '\\"\\"\\"')
        return f'"""{escaped}"""'
    if '"' in s and s.endswith('"'):
        escaped = s.replace('"', '\\"')
        return f'"""{escaped}"""'
    return f'"""{s}"""'


# =============================================================================
# Value to Python
# =============================================================================


def value_to_python(
    value: Any,
    ctx: CodegenContext,
    indent: int = 0,
) -> str:
    """Convert a value to Python source code.

    Args:
        value: The value to convert
        ctx: Code generation context
        indent: Current indentation level
    """
    indent_str = "    " * indent

    if isinstance(value, IRIntrinsic):
        result = intrinsic_to_python(value, ctx)
        if isinstance(result, AnnotatedValue):
            return annotated_to_class_ref(result)
        return result

    if value is None:
        return "None"

    if isinstance(value, bool):
        return "True" if value else "False"

    if isinstance(value, datetime.date):
        # YAML parsers often convert dates like 2012-10-17 to datetime.date objects
        # Convert back to ISO format string for CloudFormation Version fields etc.
        return repr(value.isoformat())

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, str):
        return escape_string(value)

    if isinstance(value, list):
        if not value:
            return "[]"
        if len(value) == 1:
            return f"[{value_to_python(value[0], ctx, indent)}]"
        items = [value_to_python(item, ctx, indent + 1) for item in value]
        inner = f",\n{indent_str}    ".join(items)
        return f"[\n{indent_str}    {inner},\n{indent_str}]"

    if isinstance(value, dict):
        if not value:
            return "{}"
        items = []
        for k, v in value.items():
            key_str = escape_string(k) if isinstance(k, str) else str(k)
            val_str = value_to_python(v, ctx, indent + 1)
            items.append(f"{key_str}: {val_str}")
        inner = f",\n{indent_str}    ".join(items)
        return f"{{\n{indent_str}    {inner},\n{indent_str}}}"

    return repr(value)


def annotated_to_class_ref(annotated: AnnotatedValue) -> str:
    """Convert an AnnotatedValue to a class-based ref for inline use.

    Uses no-parens pattern (bare class names passed to ref/get_att):
    - Ref[Target] -> ref(Target)
    - GetAtt[Target] with "Attr" -> get_att(Target, "Attr")
    """
    if match := re.match(r"Ref\[(\w+)\]", annotated.annotation):
        target = match.group(1)
        return f"ref({target})"
    elif match := re.match(r"GetAtt\[(\w+)\]", annotated.annotation):
        target = match.group(1)
        if attr_match := re.search(r'get_att\("(\w+)"\)', annotated.value):
            attr = attr_match.group(1)
            return f'get_att({target}, "{attr}")'
        if "(" in annotated.value:
            # Handle constants like ARN
            const = annotated.value.split("(")[1].rstrip(")")
            return f"get_att({target}, {const})"
        return f"ref({target})"
    return annotated.value


# =============================================================================
# Intrinsic to Python
# =============================================================================


def intrinsic_to_python(
    intrinsic: IRIntrinsic, ctx: CodegenContext
) -> str | AnnotatedValue:
    """Convert an IRIntrinsic to Python source code.

    Handles all CloudFormation intrinsic functions, generating appropriate
    Python expressions. May return an AnnotatedValue for top-level properties
    that need type annotations.
    """

    def _format_ref_target(logical_id: str) -> str:
        """Format a ref/get_att target - use PascalCase class names."""
        return logical_id

    if intrinsic.type == IntrinsicType.REF:
        target = intrinsic.args
        # Check if it's a pseudo-parameter
        if target.startswith("AWS::"):
            if target in PSEUDO_PARAMETER_MAP:
                const_name = PSEUDO_PARAMETER_MAP[target]
                ctx.add_intrinsic_import(const_name)
                return const_name
            ctx.add_intrinsic_import("Ref")
            return f'Ref("{target}")'
        if target in ctx.template.parameters:
            # Parameters use bare class name - no parens pattern
            return _format_ref_target(target)
        if target in ctx.template.resources:
            # Resources use bare class name - setup_resources() handles forward refs
            return _format_ref_target(target)
        ctx.add_intrinsic_import("Ref")
        return f'Ref("{target}")'

    if intrinsic.type == IntrinsicType.GET_ATT:
        logical_id, attr = intrinsic.args
        if logical_id in ctx.template.resources:
            # Use no-parens pattern: ClassName.Attr
            # setup_resources() handles forward refs via placeholders
            return f"{_format_ref_target(logical_id)}.{attr}"
        ctx.add_intrinsic_import("GetAtt")
        return f'GetAtt("{logical_id}", "{attr}")'

    if intrinsic.type == IntrinsicType.SUB:
        if isinstance(intrinsic.args, str):
            template_str = intrinsic.args
            variables = None
        else:
            template_str, variables = intrinsic.args

        # Check for ARN pattern match
        if not variables and template_str in ctx.arn_pattern_map:
            resource_id, suffix = ctx.arn_pattern_map[template_str]
            if resource_id != ctx.current_resource_id:
                var_refs = re.findall(r"\$\{([^}]+)\}", template_str)
                non_pseudo_vars = [v for v in var_refs if not v.startswith("AWS::")]
                all_params = all(v in ctx.template.parameters for v in non_pseudo_vars)
                if not all_params:
                    formatted_id = _format_ref_target(resource_id)
                    if suffix == "":
                        # Use no-parens pattern: ClassName.Arn
                        return f"{formatted_id}.Arn"
                    else:
                        # Join with .Arn suffix
                        ctx.add_intrinsic_import("Join")
                        return f"Join('', [{formatted_id}.Arn, '{suffix}'])"

        # Check for name pattern match
        if not variables and template_str in ctx.name_pattern_map:
            resource_id = ctx.name_pattern_map[template_str]
            if resource_id != ctx.current_resource_id:
                # Use bare class name - setup_resources() handles forward refs
                return _format_ref_target(resource_id)

        ctx.add_intrinsic_import("Sub")
        if variables:
            vars_str = value_to_python(variables, ctx)
            return f"Sub({escape_string(template_str)}, {vars_str})"
        return f"Sub({escape_string(template_str)})"

    if intrinsic.type == IntrinsicType.JOIN:
        ctx.add_intrinsic_import("Join")
        delimiter, values = intrinsic.args
        values_str = value_to_python(values, ctx)
        return f"Join({escape_string(delimiter)}, {values_str})"

    if intrinsic.type == IntrinsicType.SELECT:
        ctx.add_intrinsic_import("Select")
        index, list_val = intrinsic.args
        list_str = value_to_python(list_val, ctx)
        return f"Select({index}, {list_str})"

    if intrinsic.type == IntrinsicType.GET_AZS:
        ctx.add_intrinsic_import("GetAZs")
        region = intrinsic.args
        if region:
            if isinstance(region, IRIntrinsic):
                region_str = intrinsic_to_python(region, ctx)
                return f"GetAZs({region_str})"
            return f"GetAZs({escape_string(region)})"
        return "GetAZs()"

    if intrinsic.type == IntrinsicType.IF:
        ctx.add_intrinsic_import("If")
        cond_name, true_val, false_val = intrinsic.args
        true_str = value_to_python(true_val, ctx)
        false_str = value_to_python(false_val, ctx)
        return f'If("{cond_name}", {true_str}, {false_str})'

    if intrinsic.type == IntrinsicType.EQUALS:
        ctx.add_intrinsic_import("Equals")
        val1, val2 = intrinsic.args
        str1 = value_to_python(val1, ctx)
        str2 = value_to_python(val2, ctx)
        return f"Equals({str1}, {str2})"

    if intrinsic.type == IntrinsicType.AND:
        ctx.add_intrinsic_import("And")
        conditions = [value_to_python(c, ctx) for c in intrinsic.args]
        return f"And(conditions=[{', '.join(conditions)}])"

    if intrinsic.type == IntrinsicType.OR:
        ctx.add_intrinsic_import("Or")
        conditions = [value_to_python(c, ctx) for c in intrinsic.args]
        return f"Or(conditions=[{', '.join(conditions)}])"

    if intrinsic.type == IntrinsicType.NOT:
        ctx.add_intrinsic_import("Not")
        cond_str = value_to_python(intrinsic.args, ctx)
        return f"Not({cond_str})"

    if intrinsic.type == IntrinsicType.CONDITION:
        ctx.add_intrinsic_import("Condition")
        return f'Condition("{intrinsic.args}")'

    if intrinsic.type == IntrinsicType.FIND_IN_MAP:
        ctx.add_intrinsic_import("FindInMap")
        map_name, top_key, second_key = intrinsic.args
        top_str = value_to_python(top_key, ctx)
        second_str = value_to_python(second_key, ctx)
        return f'FindInMap("{map_name}", {top_str}, {second_str})'

    if intrinsic.type == IntrinsicType.BASE64:
        ctx.add_intrinsic_import("Base64")
        val_str = value_to_python(intrinsic.args, ctx)
        return f"Base64({val_str})"

    if intrinsic.type == IntrinsicType.CIDR:
        ctx.add_intrinsic_import("Cidr")
        ip_block, count, cidr_bits = intrinsic.args
        block_str = value_to_python(ip_block, ctx)
        return f"Cidr({block_str}, {count}, {cidr_bits})"

    if intrinsic.type == IntrinsicType.IMPORT_VALUE:
        ctx.add_intrinsic_import("ImportValue")
        val_str = value_to_python(intrinsic.args, ctx)
        return f"ImportValue({val_str})"

    if intrinsic.type == IntrinsicType.SPLIT:
        ctx.add_intrinsic_import("Split")
        delimiter, source = intrinsic.args
        source_str = value_to_python(source, ctx)
        return f"Split({escape_string(delimiter)}, {source_str})"

    if intrinsic.type == IntrinsicType.VALUE_OF:
        ctx.add_intrinsic_import("ValueOf")
        param_name, attr_name = intrinsic.args
        param_str = value_to_python(param_name, ctx)
        attr_str = value_to_python(attr_name, ctx)
        return f"ValueOf({param_str}, {attr_str})"

    if intrinsic.type == IntrinsicType.TRANSFORM:
        ctx.add_intrinsic_import("Transform")
        args = intrinsic.args
        if isinstance(args, list) and len(args) == 1 and isinstance(args[0], dict):
            args = args[0]
        if isinstance(args, dict):
            name = args.get("Name", "")
            params = args.get("Parameters")
            name_str = (
                escape_string(name)
                if isinstance(name, str)
                else value_to_python(name, ctx)
            )
            if params:
                params_str = value_to_python(params, ctx)
                return f"Transform(name={name_str}, parameters={params_str})"
            return f"Transform(name={name_str})"
        val_str = value_to_python(args, ctx)
        return f"Transform({val_str})"

    return f"# Unknown intrinsic: {intrinsic.type}"
