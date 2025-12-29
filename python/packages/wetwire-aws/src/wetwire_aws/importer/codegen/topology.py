"""Topological sort and cycle detection for resource dependencies.

CloudFormation resources can have circular dependencies through Ref and
GetAtt intrinsics. This module provides algorithms to:

1. Find strongly connected components (SCCs) using Tarjan's algorithm
2. Sort resources in dependency order for proper Python class definition
3. Track file-level dependencies for multi-file package generation

Note: With two-pass loading and placeholder support in dataclass-dsl,
forward references within the same file are now handled automatically.
SCC detection is still useful for grouping tightly-coupled resources
and for file-level dependency tracking.

This module uses generic graph algorithms from dataclass-dsl and adds
CloudFormation-specific graph building logic.
"""

from __future__ import annotations

import re
from typing import Any

from dataclass_dsl import find_sccs_in_graph, topological_sort_graph

from wetwire_aws.importer.ir import (
    IntrinsicType,
    IRIntrinsic,
    IRTemplate,
)

from .context import build_arn_pattern_map, build_name_pattern_map


def find_strongly_connected_components(template: IRTemplate) -> list[list[str]]:
    """Find strongly connected components using Tarjan's algorithm.

    Returns a list of SCCs, where each SCC is a list of resource IDs.
    Resources in the same SCC form a cycle and should be in the same file.
    SCCs are returned in reverse topological order (dependencies first).
    """
    # Build dependency graph from template
    graph = build_dependency_graph(template)

    # Use generic SCC algorithm from dataclass-dsl
    return find_sccs_in_graph(graph)


def build_dependency_graph(template: IRTemplate) -> dict[str, set[str]]:
    """Build a dependency graph from a CloudFormation template.

    Returns a dict mapping resource IDs to sets of resource IDs they depend on.
    """
    resources = set(template.resources.keys())
    name_pattern_map = build_name_pattern_map(template)
    arn_pattern_map = build_arn_pattern_map(template)

    graph: dict[str, set[str]] = {}
    for resource_id in resources:
        deps = find_resource_dependencies(
            template, resource_id, name_pattern_map, arn_pattern_map
        )
        graph[resource_id] = {d for d in deps if d in resources}

    return graph


def topological_sort(template: IRTemplate) -> list[str]:
    """Sort resources so dependencies come first.

    Considers both reference_graph (Ref/GetAtt) and depends_on dependencies.
    Uses the generic topological sort algorithm from dataclass-dsl.
    """
    # Build combined dependency graph (reference_graph + depends_on)
    resources = set(template.resources.keys())
    graph: dict[str, set[str]] = {}

    for resource_id in resources:
        deps: set[str] = set()

        # Add Ref/GetAtt dependencies
        for dep_id in template.reference_graph.get(resource_id, []):
            if dep_id in resources:
                deps.add(dep_id)

        # Add depends_on dependencies
        resource = template.resources.get(resource_id)
        if resource:
            for dep_id in resource.depends_on:
                if dep_id in resources:
                    deps.add(dep_id)

        graph[resource_id] = deps

    # Use generic topological sort from dataclass-dsl
    return topological_sort_graph(graph)


def find_resource_dependencies(
    template: IRTemplate,
    resource_id: str,
    name_pattern_map: dict[str, str] | None = None,
    arn_pattern_map: dict[str, tuple[str, str]] | None = None,
) -> set[str]:
    """Find other resources that this resource depends on."""
    deps = set()

    for ref_target in template.reference_graph.get(resource_id, []):
        if ref_target in template.resources and ref_target != resource_id:
            deps.add(ref_target)

    resource = template.resources.get(resource_id)
    if resource:
        _find_sub_pattern_refs(
            resource.properties,
            name_pattern_map,
            arn_pattern_map,
            resource_id,
            deps,
            template,
        )

        for dep in resource.depends_on:
            if dep in template.resources and dep != resource_id:
                deps.add(dep)

    return deps


def _find_sub_pattern_refs(
    properties: dict[str, Any],
    name_pattern_map: dict[str, str] | None,
    arn_pattern_map: dict[str, tuple[str, str]] | None,
    current_resource_id: str,
    deps: set[str],
    template: IRTemplate,
) -> None:
    """Recursively find Sub patterns that reference other resources."""
    for prop in properties.values():
        if hasattr(prop, "value"):
            _find_sub_in_value(
                prop.value,
                name_pattern_map,
                arn_pattern_map,
                current_resource_id,
                deps,
                template,
            )


def _find_sub_in_value(
    value: Any,
    name_pattern_map: dict[str, str] | None,
    arn_pattern_map: dict[str, tuple[str, str]] | None,
    current_resource_id: str,
    deps: set[str],
    template: IRTemplate,
) -> None:
    """Recursively find Sub patterns in a value."""
    if isinstance(value, IRIntrinsic):
        if value.type == IntrinsicType.SUB:
            if isinstance(value.args, str):
                template_str = value.args
            elif isinstance(value.args, (list, tuple)) and len(value.args) >= 1:
                template_str = value.args[0]
            else:
                template_str = None

            if template_str:
                var_refs = re.findall(r"\$\{([^}]+)\}", template_str)
                non_pseudo_vars = [v for v in var_refs if not v.startswith("AWS::")]
                all_params = all(v in template.parameters for v in non_pseudo_vars)

                if name_pattern_map and template_str in name_pattern_map:
                    ref_target = name_pattern_map[template_str]
                    if ref_target != current_resource_id:
                        deps.add(ref_target)
                elif arn_pattern_map and template_str in arn_pattern_map:
                    if not all_params:
                        ref_target, _ = arn_pattern_map[template_str]
                        if ref_target != current_resource_id:
                            deps.add(ref_target)

        if isinstance(value.args, (list, tuple)):
            for arg in value.args:
                _find_sub_in_value(
                    arg,
                    name_pattern_map,
                    arn_pattern_map,
                    current_resource_id,
                    deps,
                    template,
                )
        elif isinstance(value.args, dict):
            for v in value.args.values():
                _find_sub_in_value(
                    v,
                    name_pattern_map,
                    arn_pattern_map,
                    current_resource_id,
                    deps,
                    template,
                )
    elif isinstance(value, dict):
        for v in value.values():
            _find_sub_in_value(
                v,
                name_pattern_map,
                arn_pattern_map,
                current_resource_id,
                deps,
                template,
            )
    elif isinstance(value, list):
        for item in value:
            _find_sub_in_value(
                item,
                name_pattern_map,
                arn_pattern_map,
                current_resource_id,
                deps,
                template,
            )


def order_scc_resources(
    scc: list[str],
    template: IRTemplate,
    name_pattern_map: dict[str, str] | None = None,
    arn_pattern_map: dict[str, tuple[str, str]] | None = None,
) -> list[str]:
    """Order resources within an SCC to minimize forward references.

    DEPRECATED: With two-pass loading and placeholder support in dataclass-dsl,
    forward references within the same file are now handled automatically.
    This function is kept for backwards compatibility but ordering is no longer
    required for correctness.
    """
    scc_set = set(scc)

    if name_pattern_map is None:
        name_pattern_map = build_name_pattern_map(template)
    if arn_pattern_map is None:
        arn_pattern_map = build_arn_pattern_map(template)

    dep_counts: dict[str, int] = {}
    for resource_id in scc:
        deps = find_resource_dependencies(
            template, resource_id, name_pattern_map, arn_pattern_map
        )
        scc_deps = [d for d in deps if d in scc_set]
        dep_counts[resource_id] = len(scc_deps)

    return sorted(scc, key=lambda r: (dep_counts[r], r))
