# Building Domain Packages

This guide explains how to create a new wetwire domain package (e.g., wetwire-k8s, wetwire-gcp).

## Prerequisites

- Read [ARCHITECTURE.md](./ARCHITECTURE.md) to understand the three-layer design
- Familiarity with the target platform (Kubernetes, GCP, Azure, etc.)

---

## Package Structure

Create a new package following this structure:

```
wetwire-{domain}/
├── pyproject.toml
├── README.md
├── docs/
│   └── ... domain-specific documentation
├── src/wetwire_{domain}/
│   ├── __init__.py
│   ├── py.typed
│   ├── decorator.py      # @wetwire_{domain}
│   ├── provider.py       # {Domain}Provider
│   ├── context.py        # {Domain}Context
│   ├── template.py       # {Domain}Template
│   ├── base.py           # Base resource classes
│   ├── cli.py            # CLI commands
│   └── resources/        # Generated or hand-written resources
└── tests/
```

---

## Step 1: Create pyproject.toml

```toml
[project]
name = "wetwire-{domain}"
version = "0.1.0"
description = "Wetwire domain package for {Platform}"
dependencies = [
    "wetwire>=0.1.0",
]

[project.scripts]
wetwire-{domain} = "wetwire_{domain}.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## Step 2: Implement the Provider

The Provider is the core abstraction for domain-specific serialization.

```python
# src/wetwire_{domain}/provider.py
from wetwire import Provider

class {Domain}Provider(Provider):
    """Serialization provider for {Platform}."""

    name = "{domain}"

    def serialize_ref(self, source: type, target: type) -> Any:
        """
        Convert a Ref[T] to the platform's reference format.

        Examples:
        - CloudFormation: {"Ref": "LogicalId"}
        - Kubernetes: "service-name.namespace.svc.cluster.local"
        - Terraform: "${resource_type.name.id}"
        """
        # Implement platform-specific logic
        return target.__name__

    def serialize_attr(self, source: type, target: type, attr: str) -> Any:
        """
        Convert an Attr[T, "name"] to the platform's attribute reference.

        Examples:
        - CloudFormation: {"Fn::GetAtt": ["LogicalId", "Arn"]}
        - Kubernetes: {"valueFrom": {"fieldRef": {"fieldPath": "..."}}}
        - Terraform: "${resource_type.name.attribute}"
        """
        return f"{target.__name__}.{attr}"

    def serialize_resource(self, resource: Any) -> dict:
        """Convert a resource instance to the platform's format."""
        return resource.to_dict()

    def serialize_template(self, template: Any) -> Any:
        """Convert a template to the final output format."""
        return template.to_dict()
```

---

## Step 3: Extend the Context

Add platform-specific context values.

```python
# src/wetwire_{domain}/context.py
from dataclasses import dataclass
from wetwire import Context

@dataclass
class {Domain}Context(Context):
    """Context for {Platform} deployments."""

    # Add platform-specific fields
    # Example for Kubernetes:
    namespace: str = "default"
    cluster_name: str = ""

    # Example for GCP:
    # project_id: str = ""
    # region: str = ""
```

---

## Step 4: Create the Domain Decorator

Wrap the core `@wetwire` decorator with domain-specific registration.

```python
# src/wetwire_{domain}/decorator.py
from wetwire import wetwire, ResourceRegistry

# Domain-specific registry
_registry = ResourceRegistry()

def get_{domain}_registry() -> ResourceRegistry:
    """Get the {domain} resource registry."""
    return _registry

def wetwire_{domain}(cls):
    """
    Decorator for {Platform} resources.

    Usage:
        @wetwire_{domain}
        class MyResource:
            resource: Deployment
            name = "my-resource"
    """
    # Apply core decorator
    decorated = wetwire(cls)

    # Extract resource type info
    annotations = getattr(cls, "__annotations__", {})
    resource_type = annotations.get("resource")

    # Register with domain-specific type info
    type_string = getattr(resource_type, "_resource_type", "")
    _registry.register(decorated, type_string)

    return decorated
```

---

## Step 5: Implement the Template

Create a domain-specific template for output generation.

```python
# src/wetwire_{domain}/template.py
from wetwire import Template, topological_sort
from wetwire_{domain}.decorator import get_{domain}_registry
from wetwire_{domain}.provider import {Domain}Provider

class {Domain}Template(Template):
    """Template for {Platform} output."""

    def __init__(self, description: str = ""):
        super().__init__(description=description)
        self.provider = {Domain}Provider()

    @classmethod
    def from_registry(
        cls,
        scope_package: str | None = None,
        description: str = "",
    ) -> "{Domain}Template":
        """Build template from registered resources."""
        registry = get_{domain}_registry()
        template = cls(description=description)

        # Get resources in dependency order
        resources = list(registry.get_all(scope_package))
        ordered = topological_sort(resources)  # Use core utility!

        for resource_cls in ordered:
            template.add_resource(resource_cls())

        return template

    def to_dict(self) -> dict:
        """Convert to platform-specific format."""
        # Implement platform-specific structure
        return {
            "resources": [
                self.provider.serialize_resource(r)
                for r in self.resources
            ]
        }
```

---

## Step 6: Build the CLI

Use core CLI utilities for consistency.

```python
# src/wetwire_{domain}/cli.py
import argparse
from wetwire import (
    add_common_args,
    create_list_command,
    create_validate_command,
    discover_resources,
)
from wetwire_{domain}.decorator import get_{domain}_registry
from wetwire_{domain}.template import {Domain}Template

def get_resource_type(cls: type) -> str:
    """Extract resource type from a wrapper class."""
    annotations = getattr(cls, "__annotations__", {})
    resource_type = annotations.get("resource")
    return getattr(resource_type, "_resource_type", "Unknown")

def build_command(args: argparse.Namespace) -> None:
    """Generate output from registered resources."""
    registry = get_{domain}_registry()

    if args.modules:
        for module in args.modules:
            discover_resources(module, registry, args.verbose)

    template = {Domain}Template.from_registry(scope_package=args.scope)
    print(template.to_json(indent=2))

def main() -> None:
    registry = get_{domain}_registry()

    parser = argparse.ArgumentParser(prog="wetwire-{domain}")
    subparsers = parser.add_subparsers(dest="command")

    # Build command (domain-specific)
    build_parser = subparsers.add_parser("build")
    add_common_args(build_parser)  # Reuse core args!
    build_parser.set_defaults(func=build_command)

    # List command (use core factory)
    list_parser = subparsers.add_parser("list")
    add_common_args(list_parser)
    list_parser.set_defaults(
        func=create_list_command(registry, get_resource_type)
    )

    # Validate command (use core factory)
    validate_parser = subparsers.add_parser("validate")
    add_common_args(validate_parser)
    validate_parser.set_defaults(
        func=create_validate_command(registry)
    )

    args = parser.parse_args()
    if args.command:
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
```

---

## Step 7: Define Resource Base Classes

Create base classes for resources in your domain.

```python
# src/wetwire_{domain}/base.py
from dataclasses import dataclass
from typing import Any

@dataclass
class {Domain}Resource:
    """Base class for {Platform} resources."""

    _resource_type: str = ""  # Override in subclasses

    def to_dict(self) -> dict[str, Any]:
        """Convert to platform format."""
        result = {}
        for field_name, value in self.__dict__.items():
            if not field_name.startswith("_") and value is not None:
                result[self._to_key_name(field_name)] = self._serialize(value)
        return result

    def _to_key_name(self, name: str) -> str:
        """Convert Python name to platform key name."""
        # Override for platform conventions (camelCase, PascalCase, etc.)
        return name

    def _serialize(self, value: Any) -> Any:
        """Serialize a value."""
        if hasattr(value, "to_dict"):
            return value.to_dict()
        if isinstance(value, list):
            return [self._serialize(v) for v in value]
        if isinstance(value, dict):
            return {k: self._serialize(v) for k, v in value.items()}
        return value
```

---

## Checklist

Before releasing your domain package:

- [ ] Provider implements all abstract methods
- [ ] Context has platform-specific fields
- [ ] Template uses core `topological_sort`
- [ ] CLI uses core utilities (`add_common_args`, `create_*_command`)
- [ ] Decorator wraps core `@wetwire`
- [ ] Tests cover serialization and dependency ordering
- [ ] Documentation explains platform-specific concepts
- [ ] `py.typed` marker is present for type checking

---

## Example: wetwire-k8s Skeleton

See the [wetwire-aws](../packages/wetwire-aws/) package for a complete reference implementation.

A Kubernetes package would differ in:
- Output is a list of manifests, not a nested template
- References become DNS names or environment variables
- No intrinsic functions (Ref, GetAtt are CloudFormation-specific)
- Resources have `apiVersion`, `kind`, `metadata`, `spec` structure
