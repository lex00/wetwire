# Wetwire Specification

**Version:** 0.1
**Status:** Draft
**Last Updated:** 2024-12-26

## Abstract

This document specifies the Wetwire pattern for building declarative domain-specific languages (DSLs) using dataclasses. The pattern is language-agnostic and can be implemented in Python, Go, Rust, TypeScript, or any language with similar capabilities.

Wetwire is designed for infrastructure-as-code, configuration management, and schema-driven systems where resources form a graph of relationships.

---

## 1. Design Principles

### 1.1 Flat by Default

Declarations SHOULD avoid unnecessary nesting or constructor calls. Configuration is expressed as field assignments, not method chains.

```
# GOOD: Flat declaration
class MyDatabase:
    resource: DatabaseInstance
    instance_class = "db.t3.micro"
    storage_size = 100

# AVOID: Nested/imperative
database = DatabaseInstance(
    instance_class="db.t3.micro",
    storage_size=100
)
```

### 1.2 No Parens for Wiring

Resource relationships SHOULD be expressed as class references, not function calls.

```
# GOOD: No parens
network = MyNetwork
role_arn = MyRole.Arn
subnets = [Subnet1, Subnet2, Subnet3]

# AVOID: Function calls for wiring
network = ref(MyNetwork)
role_arn = get_att(MyRole, "Arn")
subnets = [ref(S1), ref(S2), ref(S3)]
```

### 1.3 The Paren Boundary

Parentheses are appropriate for:
- Intrinsic functions: `Sub()`, `Join()`, `If()`
- Conditional values: `when()`, `match()`
- Replication: `ForEach()`
- External data: `Import()`, `Parameter()`

The 90% case (wiring resources) is paren-free. The 10% case (logic, computation) uses explicit calls.

### 1.4 Type-Safe Without Ceremony

Type annotations provide safety without boilerplate. Implementations SHOULD integrate with language type checkers.

### 1.5 Graph-Native

Resources and their relationships are first-class concepts. The system understands that resources reference each other and can compute dependency ordering.

---

## 2. Wrapper Pattern

### 2.1 Definition

A **wrapper class** is a user-defined class that wraps a domain object (resource, configuration, entity) with a declarative interface.

```
@wetwire
class MyBucket:
    resource: Bucket           # Declares the underlying type
    bucket_name = "data"       # Configuration field
    encryption = MyEncryption  # Reference to another wrapper
```

### 2.2 Requirements

A wrapper class MUST:
1. Declare the underlying resource type via a `resource` field (or equivalent)
2. Express configuration as class-level field assignments
3. Be processed by a decorator that handles registration and serialization

### 2.3 Field Types

| Field Type | Example | Meaning |
|------------|---------|---------|
| Literal | `name = "data"` | Static value |
| Reference | `vpc = MyVPC` | Reference to another wrapper |
| Attribute Reference | `arn = MyRole.Arn` | Reference to specific attribute |
| List of References | `subnets = [S1, S2]` | Collection of references |
| Dict with References | `env = {"DB": MyDB}` | Map containing references |

---

## 3. Reference Detection

### 3.1 Implicit References

When a class attribute's value is another wrapper class, implementations MUST detect this as a reference relationship.

```
@wetwire
class MySubnet:
    resource: Subnet
    network = MyNetwork  # Detected as Ref[MyNetwork]
```

### 3.2 Attribute References

When a class attribute's value is an attribute access on another wrapper class, implementations MUST detect this as an attribute reference.

```
@wetwire
class MyFunction:
    resource: Function
    role = MyRole.Arn  # Detected as Attr[MyRole, "Arn"]
```

### 3.3 Collection Processing

Implementations MUST recursively process lists and dicts for references:

```
@wetwire
class MyFunction:
    resource: Function
    security_groups = [SG1, SG2, SG3]  # Each element is a reference
    environment = {
        "DB_HOST": MyDatabase,          # Reference
        "DB_ARN": MyDatabase.Arn,       # Attribute reference
        "REGION": "us-east-1",          # Literal (pass through)
    }
```

---

## 4. Decorator Behavior

### 4.1 Required Behavior

A conforming decorator MUST:

1. **Transform** the decorated class into a dataclass (or equivalent)
2. **Register** the class in a registry for later discovery
3. **Detect** reference patterns in class attributes
4. **Provide** serialization to the target format

### 4.2 Recommended Behavior

A conforming decorator SHOULD:

1. Integrate with the language's type checker (e.g., `@dataclass_transform` in Python)
2. Support the no-parens reference patterns
3. Preserve the class for introspection

### 4.3 Type Checker Integration

In Python, decorators SHOULD use `@dataclass_transform` (PEP 681):

```python
from typing import dataclass_transform

@dataclass_transform()
def wetwire(cls):
    # Implementation
    return cls
```

---

## 5. Registry Pattern

### 5.1 Purpose

The registry enables template builders to discover all declared resources without explicit wiring.

### 5.2 Interface

```
class Registry:
    register(cls, resource_type) -> None
    get_all(scope_package=None) -> list[type]
    get_by_type(resource_type) -> list[type]
```

### 5.3 Scoped Discovery

Implementations MUST support filtering by scope (package/module) to prevent pollution across unrelated codebases:

```
# Only resources from this package
resources = registry.get_all(scope_package="my_project.resources")
```

### 5.4 Thread Safety

Registry implementations MUST be thread-safe for concurrent registration and lookup.

---

## 6. Template Pattern

### 6.1 Purpose

The Template aggregates resources from the registry and provides serialization to the target format.

### 6.2 Interface

```
class Template:
    @classmethod
    from_registry(scope_package=None, context=None) -> Template

    to_dict() -> dict
    to_json() -> str
    to_yaml() -> str
```

### 6.3 Resource Ordering

Templates MUST serialize resources in dependency order. Resources that are referenced by other resources MUST appear before the resources that reference them.

---

## 7. Context Pattern

### 7.1 Purpose

Context provides environment-specific values resolved at serialization time.

### 7.2 Interface

```
class Context:
    project: str
    environment: str
    region: str | None
```

### 7.3 Context References

Resources can reference context values using `ContextRef`:

```
@wetwire
class MyResource:
    resource: SomeType
    name = ContextRef("project")  # Resolved at serialization
```

### 7.4 Pseudo-Parameters

Implementations MAY define pre-built context references:

```
PROJECT = ContextRef("project")
ENVIRONMENT = ContextRef("environment")
REGION = ContextRef("region")
```

---

## 8. Provider Interface

### 8.1 Purpose

For DSLs targeting multiple output formats, providers abstract format-specific serialization.

### 8.2 Interface

```
class Provider:
    name: str

    serialize_ref(source, target) -> Any
    serialize_attr(source, target, attr_name) -> Any
    serialize_template(template) -> str
```

### 8.3 Examples

| Provider | Output Format | Reference Format |
|----------|---------------|------------------|
| CloudFormation | JSON | `{"Ref": "LogicalId"}` |
| Config Connector | YAML | `name: resource-name` |
| ARM | JSON | `[resourceId(...)]` |
| Kubernetes | YAML | `name: resource-name` |

---

## 9. Serialization Contract

### 9.1 Requirements

Serialization MUST:
1. Resolve references to the provider-specific format
2. Handle attribute references appropriately
3. Process nested configurations recursively
4. Omit fields with `None` values (unless explicitly required)

### 9.2 Property Mapping

Implementations MUST support mapping between language-idiomatic names and target format names:

```
# Python uses snake_case
bucket_name = "data"

# Serializes to CloudFormation PascalCase
{"BucketName": "data"}
```

---

## 10. Dependency Graph

### 10.1 Computation

Implementations MUST compute dependencies from reference analysis:

```
def get_dependencies(cls) -> set[type]:
    """Return all classes this resource directly depends on."""

def get_dependencies(cls, transitive=True) -> set[type]:
    """Return all classes this resource depends on, transitively."""
```

### 10.2 Topological Sort

Resources MUST be ordered so dependencies appear before dependents.

### 10.3 Circular Dependencies

When circular dependencies exist (A → B → A):
1. Group into strongly connected components
2. Place together in output
3. Generate explicit dependency hints if the format supports them

---

## 11. Presets and Traits

### 11.1 Presets (Inheritance-Based Defaults)

Base classes can provide default configurations:

```
class EncryptedStorage:
    def __init_subclass__(cls, **kwargs):
        if not hasattr(cls, 'encryption'):
            cls.encryption = DefaultEncryption

@wetwire
class MyBucket(EncryptedStorage):
    resource: Bucket
    name = "data"
    # encryption inherited
```

### 11.2 Traits (Cross-Cutting Concerns)

Traits apply configurations via class parameters:

```
class Tagged:
    def __init_subclass__(cls, environment: str, team: str, **kwargs):
        cls._tags = [("Environment", environment), ("Team", team)]

@wetwire
class MyBucket(Tagged, environment="prod", team="platform"):
    resource: Bucket
```

---

## 12. Computed Values

### 12.1 Purpose

Computed values are derived from other fields at serialization time.

### 12.2 Syntax

```
@wetwire
class MyBucket:
    resource: Bucket
    project: str
    environment: str

    @computed
    def name(self) -> str:
        return f"{self.project}-{self.environment}-data"
```

### 12.3 Requirements

Computed values MUST:
1. Be evaluated at serialization time, not class definition time
2. Have access to resolved context values
3. Be cacheable (same inputs produce same outputs)

---

## 13. Conditional Values

### 13.1 Purpose

Conditional values allow configuration to vary based on context.

### 13.2 Syntax

```
@wetwire
class MyDatabase:
    resource: Database
    instance_class = when(
        ENVIRONMENT == "production",
        then="db.r5.large",
        else_="db.t3.micro"
    )
```

### 13.3 Requirements

Conditional helpers MUST:
1. Be evaluated at serialization time
2. Have access to context values
3. Support the target format's native conditionals when available

---

## 14. Forward References

### 14.1 Problem

When Class A references Class B which is defined later, the reference cannot be resolved at class definition time.

### 14.2 Solutions

Implementations MUST support at least one of:
1. **Deferred resolution** — Store class names as strings, resolve at serialization
2. **Two-phase initialization** — Register all classes first, resolve references second
3. **Registry lookup** — `network = "MyNetwork"` with registry-based resolution

---

## 15. Conformance

### 15.1 Levels

| Level | Requirements |
|-------|--------------|
| Minimal | Wrapper pattern, reference detection, registry, serialization |
| Standard | + Context, Provider interface, dependency ordering |
| Full | + Presets, Traits, Computed values, Conditionals |

### 15.2 Validation

Implementations SHOULD provide validation that:
1. All references resolve to registered classes
2. No circular dependencies exist (or are handled appropriately)
3. Required fields are provided
4. Type annotations match assigned values

---

## Appendix: Related Specifications

- [GRAPH_REFS_SPEC.md](GRAPH_REFS_SPEC.md) — Typing primitives specification

### Language-Specific Implementation Notes

See the language-specific documentation for implementation details:
- Python: `python/docs/IMPLEMENTATION_PLAN.md`
