# Wetwire Architecture

This document describes the layered architecture of the wetwire framework and how domain packages should be structured.

## Three-Layer Design

```
┌─────────────────────────────────────────────┐
│           Domain Packages                   │
│  (wetwire-aws, wetwire-k8s, wetwire-gcp)   │
├─────────────────────────────────────────────┤
│           wetwire (core)                    │
│  decorator, registry, template, provider   │
├─────────────────────────────────────────────┤
│           graph-refs                        │
│  Ref[T], Attr[T], dependency introspection │
└─────────────────────────────────────────────┘
```

Each layer has specific responsibilities and dependencies only flow downward.

---

## Layer 1: graph-refs (Typing Library)

**Purpose:** Provide type annotations for expressing resource references.

**Key exports:**
- `Ref[T]` - Reference to another resource
- `Attr[T, "name"]` - Reference to a specific attribute
- `RefList[T]` - List of references
- `ContextRef["name"]` - Reference to context values
- `get_refs(cls)` - Introspect references from type hints
- `get_dependencies(cls)` - Compute dependency graph

**Characteristics:**
- Zero runtime dependencies
- Works with any Python type checker (mypy, pyright)
- Domain-agnostic (knows nothing about AWS, K8s, etc.)

**Example:**
```python
from graph_refs import Ref, Attr

class MySubnet:
    vpc: Ref[MyVPC]                    # Reference to VPC
    role: Attr[MyRole, "Arn"]          # Reference to Role's Arn attribute
```

---

## Layer 2: wetwire (Core Framework)

**Purpose:** Provide domain-agnostic infrastructure for building declarative DSLs.

**Key modules:**

| Module | Purpose |
|--------|---------|
| `decorator.py` | `@wetwire` decorator with dataclass transform |
| `registry.py` | `ResourceRegistry` for tracking decorated classes |
| `template.py` | `Template` base class for output generation |
| `provider.py` | `Provider` ABC for domain-specific serialization |
| `context.py` | `Context` base for environment/project values |
| `ordering.py` | `topological_sort`, `get_creation_order`, cycle detection |
| `cli.py` | CLI utilities: `discover_resources`, `add_common_args` |
| `computed.py` | `@computed` decorator for derived fields |
| `conditions.py` | `when()`, `match()` conditional helpers |

**Characteristics:**
- Depends only on graph-refs
- No domain-specific code (no AWS, K8s, GCP references)
- Provides extension points (Provider ABC, Context base)

**What domain packages inherit:**
```python
from wetwire import (
    wetwire,              # Base decorator
    Template,             # Template base class
    Provider,             # Serialization ABC
    Context,              # Context base class
    registry,             # Global registry
    topological_sort,     # Dependency ordering
    discover_resources,   # CLI helper
    add_common_args,      # CLI helper
    create_list_command,  # CLI command factory
    create_validate_command,  # CLI command factory
)
```

---

## Layer 3: Domain Packages (e.g., wetwire-aws)

**Purpose:** Implement domain-specific resource types, serialization, and tooling.

**What each domain package provides:**

| Component | Example (AWS) | Example (K8s) |
|-----------|---------------|---------------|
| **Decorator** | `@wetwire_aws` | `@wetwire_k8s` |
| **Provider** | `CloudFormationProvider` | `KubernetesProvider` |
| **Context** | `AWSContext` (region, account) | `K8sContext` (namespace, cluster) |
| **Base classes** | `CloudFormationResource` | `KubernetesResource` |
| **Intrinsics** | `Ref`, `GetAtt`, `Sub` | N/A (K8s doesn't have these) |
| **Template** | `CloudFormationTemplate` | `KubernetesManifest` |
| **Resources** | Generated from CF spec | Generated from K8s API |
| **CLI** | `wetwire-aws build` | `wetwire-k8s apply` |

---

## Dependency Graph

```
graph-refs (no dependencies)
    │
    ▼
wetwire (depends: graph-refs)
    │
    ├──────────────────┬──────────────────┐
    ▼                  ▼                  ▼
wetwire-aws        wetwire-k8s       wetwire-gcp
(depends: wetwire) (depends: wetwire) (depends: wetwire)
```

---

## Extension Points

### Provider ABC

The `Provider` class defines how references are serialized:

```python
from abc import ABC, abstractmethod

class Provider(ABC):
    name: str  # e.g., "cloudformation", "kubernetes"

    @abstractmethod
    def serialize_ref(self, source: type, target: type) -> Any:
        """Serialize a Ref[T] reference."""
        pass

    @abstractmethod
    def serialize_attr(self, source: type, target: type, attr: str) -> Any:
        """Serialize an Attr[T, name] reference."""
        pass

    @abstractmethod
    def serialize_resource(self, resource: Any) -> dict:
        """Serialize a resource instance."""
        pass
```

**CloudFormation implementation:**
```python
class CloudFormationProvider(Provider):
    name = "cloudformation"

    def serialize_ref(self, source, target):
        return {"Ref": target.__name__}

    def serialize_attr(self, source, target, attr):
        return {"Fn::GetAtt": [target.__name__, attr]}
```

**Kubernetes implementation (hypothetical):**
```python
class KubernetesProvider(Provider):
    name = "kubernetes"

    def serialize_ref(self, source, target):
        # K8s uses DNS names for service discovery
        return f"{target.__name__.lower()}.default.svc.cluster.local"

    def serialize_attr(self, source, target, attr):
        # K8s uses environment variables
        return {"valueFrom": {"fieldRef": {"fieldPath": attr}}}
```

### Context Extension

The `Context` base class holds environment values:

```python
from dataclasses import dataclass
from wetwire import Context

@dataclass
class AWSContext(Context):
    region: str = "us-east-1"
    account_id: str = ""
    stack_name: str = ""

@dataclass
class K8sContext(Context):
    namespace: str = "default"
    cluster_name: str = ""
```

### Decorator Wrapping

Domain decorators wrap the core `@wetwire`:

```python
from wetwire import wetwire, ResourceRegistry

_aws_registry = ResourceRegistry()

def wetwire_aws(cls):
    """AWS-specific decorator."""
    decorated = wetwire(cls)  # Use core decorator

    # AWS-specific registration
    resource_type = cls.__annotations__.get("resource")
    cf_type = getattr(resource_type, "_resource_type", "")
    _aws_registry.register(decorated, cf_type)

    return decorated
```

---

## Best Practices for Domain Packages

### DO:
- Reuse core decorator, registry, and CLI utilities
- Implement Provider ABC for domain-specific serialization
- Extend Context for domain-specific values
- Use `topological_sort` from core for dependency ordering

### DON'T:
- Reimplement topological sorting
- Duplicate serialization logic
- Put domain-specific code in wetwire core
- Import directly from graph-refs (use wetwire re-exports)

---

## File Organization

```
python/
├── docs/
│   ├── ARCHITECTURE.md              # This document
│   ├── BUILDING_DOMAIN_PACKAGES.md  # Guide for new domains
│   └── IMPLEMENTATION_PLAN.md       # Phase roadmap
│
└── packages/
    ├── wetwire/                     # Core framework
    │   └── src/wetwire/
    │       ├── decorator.py
    │       ├── registry.py
    │       ├── template.py
    │       ├── provider.py
    │       ├── context.py
    │       ├── ordering.py
    │       └── cli.py
    │
    └── wetwire-aws/                 # AWS domain package
        ├── docs/
        │   ├── CODEGEN.md           # AWS-specific codegen
        │   └── CF_INTERNALS.md      # CloudFormation details
        └── src/wetwire_aws/
            ├── decorator.py         # @wetwire_aws
            ├── template.py          # CloudFormationTemplate
            ├── base.py              # CloudFormationResource
            ├── intrinsics/          # Ref, GetAtt, Sub, etc.
            └── resources/           # Generated resource types
```
