"""
Wetwire: Declarative dataclass framework for infrastructure-as-code.

Wetwire provides a decorator and utilities for building declarative DSLs
using Python dataclasses with typed references.

Example:
    >>> from wetwire import wetwire, Template
    >>>
    >>> @wetwire
    ... class MyNetwork:
    ...     resource: VPC
    ...     cidr_block = "10.0.0.0/16"
    ...
    >>> @wetwire
    ... class MySubnet:
    ...     resource: Subnet
    ...     vpc = MyNetwork  # Reference to MyNetwork
    ...     cidr_block = "10.0.1.0/24"
    ...
    >>> template = Template.from_registry()
"""

__version__ = "0.1.0"

# Core decorator
# graph-refs types for reference annotations
from graph_refs import (
    Attr,
    ContextRef,
    Ref,
    RefDict,
    RefInfo,
    RefList,
    get_refs,
)
from graph_refs import (
    get_dependencies as get_ref_dependencies,
)

# CLI utilities
from wetwire.cli import (
    add_common_args,
    create_list_command,
    create_validate_command,
    discover_resources,
)

# Resource loader
from wetwire.loader import setup_resources

# Stub generation
from wetwire.stubs import StubConfig

# Computed fields
from wetwire.computed import computed

# Conditional values
from wetwire.conditions import match, when

# Context
from wetwire.context import ENVIRONMENT, PROJECT, Context
from wetwire.decorator import wetwire

# Ordering utilities
from wetwire.ordering import (
    detect_cycles,
    get_creation_order,
    get_deletion_order,
    get_dependency_graph,
    topological_sort,
)

# Provider
from wetwire.provider import Provider

# Registry
from wetwire.registry import ResourceRegistry, registry

# Template
from wetwire.template import Template

__all__ = [
    # Version
    "__version__",
    # Decorator
    "wetwire",
    # Registry
    "registry",
    "ResourceRegistry",
    # Template
    "Template",
    # Provider
    "Provider",
    # Context
    "Context",
    "PROJECT",
    "ENVIRONMENT",
    # Computed
    "computed",
    # Conditions
    "when",
    "match",
    # Ordering
    "topological_sort",
    "get_creation_order",
    "get_deletion_order",
    "detect_cycles",
    "get_dependency_graph",
    # CLI utilities
    "discover_resources",
    "add_common_args",
    "create_list_command",
    "create_validate_command",
    # graph-refs types
    "Ref",
    "Attr",
    "RefList",
    "RefDict",
    "ContextRef",
    "RefInfo",
    "get_refs",
    "get_ref_dependencies",
    # Resource loader
    "setup_resources",
    # Stub generation
    "StubConfig",
]
