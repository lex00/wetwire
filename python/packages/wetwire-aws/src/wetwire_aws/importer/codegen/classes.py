"""Class generation functions for CloudFormation elements.

This module generates Python dataclass definitions for CloudFormation
template elements.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from wetwire_aws.importer.ir import (
    IRCondition,
    IRMapping,
    IROutput,
    IRParameter,
    IRResource,
)

from .context import AnnotatedValue
from .helpers import (
    PARAMETER_TYPE_MAP,
    resolve_resource_type,
    sanitize_class_name,
)
from .values import escape_docstring, escape_string, value_to_python

if TYPE_CHECKING:
    from .context import CodegenContext


# =============================================================================
# Parameter Class Generation
# =============================================================================


def generate_parameter_class(param: IRParameter, ctx: "CodegenContext") -> str:
    """Generate a Parameter wrapper class definition."""
    lines = []

    # Docstring
    if ctx.include_docstrings and param.description:
        lines.append(f"    {escape_docstring(param.description)}")
        lines.append("")

    # Resource type annotation
    ctx.add_import("wetwire_aws", "Parameter")
    lines.append("    resource: Parameter")

    # Type - use constant if available
    if param.type in PARAMETER_TYPE_MAP:
        const_name = PARAMETER_TYPE_MAP[param.type]
        ctx.add_import("wetwire_aws", const_name)
        lines.append(f"    type = {const_name}")
    else:
        lines.append(f"    type = {escape_string(param.type)}")

    # Optional fields
    if param.description:
        lines.append(f"    description = {escape_string(param.description)}")
    if param.default is not None:
        lines.append(f"    default = {value_to_python(param.default, ctx)}")
    if param.allowed_values:
        lines.append(f"    allowed_values = {value_to_python(param.allowed_values, ctx)}")
    if param.allowed_pattern:
        lines.append(f"    allowed_pattern = {escape_string(param.allowed_pattern)}")
    if param.min_length is not None:
        lines.append(f"    min_length = {param.min_length}")
    if param.max_length is not None:
        lines.append(f"    max_length = {param.max_length}")
    if param.min_value is not None:
        lines.append(f"    min_value = {param.min_value}")
    if param.max_value is not None:
        lines.append(f"    max_value = {param.max_value}")
    if param.constraint_description:
        lines.append(f"    constraint_description = {escape_string(param.constraint_description)}")
    if param.no_echo:
        lines.append("    no_echo = True")

    ctx.add_import("wetwire_aws", "wetwire_aws")

    class_name = sanitize_class_name(param.logical_id)
    return f"@wetwire_aws\nclass {class_name}:\n" + "\n".join(lines)


# =============================================================================
# Resource Class Generation
# =============================================================================


def generate_resource_class(resource: IRResource, ctx: "CodegenContext") -> str:
    """Generate a resource wrapper class."""
    ctx.current_resource_id = resource.logical_id
    lines = []

    # Docstring
    if ctx.include_docstrings:
        lines.append(f'    """{resource.resource_type} resource."""')
        lines.append("")

    # Resolve resource type
    resolved = resolve_resource_type(resource.resource_type)

    if resolved:
        module, class_name = resolved
        ctx.current_module = module

        # Always use qualified imports: resource: apprunner.Service
        # This ensures the module is available via `from . import *`
        # since __init__.py imports modules (not classes)
        ctx.add_import("wetwire_aws.resources", module)
        lines.append(f"    resource: {module}.{class_name}")
    else:
        # Unknown resource type
        lines.append(f"    # Unknown resource type: {resource.resource_type}")
        lines.append("    resource: CloudFormationResource")
        ctx.add_import("wetwire_aws.base", "CloudFormationResource")

    # Properties
    for prop in resource.properties.values():
        value_result = value_to_python(prop.value, ctx)
        if isinstance(value_result, AnnotatedValue):
            lines.append(f"    {prop.python_name}: {value_result.annotation} = {value_result.value}")
        else:
            lines.append(f"    {prop.python_name} = {value_result}")

    # Resource-level attributes
    if resource.depends_on:
        deps = ", ".join(f'"{d}"' for d in resource.depends_on)
        lines.append(f"    depends_on = [{deps}]")
    if resource.condition:
        lines.append(f"    condition = {escape_string(resource.condition)}")
    if resource.deletion_policy:
        lines.append(f"    deletion_policy = {escape_string(resource.deletion_policy)}")

    ctx.add_import("wetwire_aws", "wetwire_aws")

    class_name = sanitize_class_name(resource.logical_id)
    return f"@wetwire_aws\nclass {class_name}:\n" + "\n".join(lines)


# =============================================================================
# Output Class Generation
# =============================================================================


def generate_output_class(output: IROutput, ctx: "CodegenContext") -> str:
    """Generate an output wrapper class."""
    lines = []

    # Docstring
    if ctx.include_docstrings and output.description:
        lines.append(f"    {escape_docstring(output.description)}")
        lines.append("")

    ctx.add_import("wetwire_aws", "Output")
    lines.append("    resource: Output")

    # Value
    value_str = value_to_python(output.value, ctx, indent=1)
    lines.append(f"    value = {value_str}")

    # Optional fields
    if output.description:
        lines.append(f"    description = {escape_string(output.description)}")
    if output.export_name:
        export_str = value_to_python(output.export_name, ctx, indent=1)
        lines.append(f"    export_name = {export_str}")
    if output.condition:
        lines.append(f"    condition = {escape_string(output.condition)}")

    ctx.add_import("wetwire_aws", "wetwire_aws")

    class_name = sanitize_class_name(output.logical_id)
    return f"@wetwire_aws\nclass {class_name}Output:\n" + "\n".join(lines)


# =============================================================================
# Mapping Class Generation
# =============================================================================


def generate_mapping_class(mapping: IRMapping, ctx: "CodegenContext") -> str:
    """Generate a mapping wrapper class."""
    lines = []

    ctx.add_import("wetwire_aws", "Mapping")
    lines.append("    resource: Mapping")

    # Map data as dict
    map_str = value_to_python(mapping.map_data, ctx, indent=1)
    lines.append(f"    map_data = {map_str}")

    ctx.add_import("wetwire_aws", "wetwire_aws")

    class_name = sanitize_class_name(mapping.logical_id)
    return f"@wetwire_aws\nclass {class_name}Mapping:\n" + "\n".join(lines)


# =============================================================================
# Condition Class Generation
# =============================================================================


def generate_condition_class(condition: IRCondition, ctx: "CodegenContext") -> str:
    """Generate a condition wrapper class."""
    lines = []

    ctx.add_import("wetwire_aws", "Condition as TemplateCondition")
    lines.append("    resource: TemplateCondition")

    # Store the original logical ID for CloudFormation serialization
    lines.append(f"    logical_id = {escape_string(condition.logical_id)}")

    # Expression
    expr_str = value_to_python(condition.expression, ctx, indent=1)
    lines.append(f"    expression = {expr_str}")

    ctx.add_import("wetwire_aws", "wetwire_aws")

    class_name = sanitize_class_name(condition.logical_id)
    return f"@wetwire_aws\nclass {class_name}Condition:\n" + "\n".join(lines)
