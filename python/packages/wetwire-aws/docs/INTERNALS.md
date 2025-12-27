# Internals

This document covers the internal architecture of wetwire-aws for contributors and maintainers.

**Contents:**
- [Resource Registry](#resource-registry) - How auto-registration works
- [Template Generation](#template-generation) - How templates are built
- [graph-refs Integration](#graph-refs-integration) - Dependency introspection
- [AWS Resource Generator](#aws-resource-generator) - Code generation architecture

---

## Resource Registry

wetwire-aws uses the `ResourceRegistry` from wetwire (core) for resource registration and discovery.

### How It Works

When you decorate a class with `@wetwire_aws`, it automatically registers with the AWS registry:

```python
@wetwire_aws
class MyBucket:
    resource: Bucket
    bucket_name = "data"
    # Automatically registered with resource type "AWS::S3::Bucket"
```

The decorator:
1. Applies `@wetwire` from the core package for dataclass transformation
2. Extracts the resource type from the `resource` annotation
3. Registers the class with the AWS-specific registry

### Registry API

```python
from wetwire_aws.decorator import get_aws_registry

registry = get_aws_registry()

# Get all registered resources
all_resources = list(registry.get_all())

# Get resources in a specific scope/package
scoped = list(registry.get_all("myapp.infra"))

# Clear for test isolation
registry.clear()
```

### Test Isolation

Use `registry.clear()` in test fixtures:

```python
@pytest.fixture(autouse=True)
def clear_registry():
    get_aws_registry().clear()
    yield
    get_aws_registry().clear()
```

---

## Template Generation

The `CloudFormationTemplate` class collects registered resources and generates CloudFormation JSON or YAML.

### from_registry()

```python
template = CloudFormationTemplate.from_registry(
    scope_package="myapp.infra",  # Optional: filter by package
    description="My Stack",
)
```

The method:
1. Gets all registered resources (optionally filtered by scope)
2. **Topologically sorts** resources by dependencies using graph-refs
3. Resolves `Ref[T]` and `Attr[T, "name"]` annotations to intrinsics
4. Creates CloudFormation resource definitions

### Topological Sorting

Resources are ordered so dependencies come before dependents:

```python
from graph_refs import get_dependencies

# NetworkBucket has no deps
# SubnetBucket depends on NetworkBucket
# InstanceBucket depends on SubnetBucket

# After topological sort:
# 1. NetworkBucket
# 2. SubnetBucket
# 3. InstanceBucket
```

The `_topological_sort()` method uses Kahn's algorithm:
1. Find resources with no unsatisfied dependencies
2. Add them to the result
3. Repeat until all resources are placed
4. Fall back to alphabetical order for circular dependencies

### Reference Resolution

`resolve_refs_from_annotations()` converts graph-refs types to CloudFormation intrinsics:

| graph-refs Type | CloudFormation Output |
|-----------------|----------------------|
| `Ref[MyBucket]` | `{"Ref": "MyBucket"}` |
| `Attr[MyRole, "Arn"]` | `{"Fn::GetAtt": ["MyRole", "Arn"]}` |
| `ContextRef["AWS::Region"]` | `{"Ref": "AWS::Region"}` |
| `RefList[MySecurityGroup]` | (handled at value level) |

---

## graph-refs Integration

wetwire-aws uses graph-refs for dependency introspection and reference resolution.

### Type Annotations

```python
# Import reference types from wetwire (core package)
from wetwire import Ref, Attr, ContextRef, RefList

@wetwire_aws
class MyFunction:
    resource: Function
    # These annotations enable introspection
    role: Attr[MyRole, "Arn"] = None
    bucket: Ref[MyBucket] = None
    region: ContextRef["AWS::Region"] = None
    security_groups: RefList[SecurityGroup] = None
```

### Introspection API

```python
from wetwire import get_refs, get_ref_dependencies

# Get all references from a class
refs = get_refs(MyFunction)
# Returns: {"role": RefInfo(target=MyRole, attr="Arn"), ...}

# Get dependency classes
deps = get_ref_dependencies(MyFunction)
# Returns: {MyRole, MyBucket}

# Transitive dependencies
all_deps = get_ref_dependencies(MyFunction, transitive=True)
```

### Validation

The CLI uses graph-refs to validate references:

```bash
wetwire-aws validate --module myapp.infra
```

Checks:
- All referenced classes exist in the registry
- No dangling references
- Dependency graph is valid

---

## AWS Resource Generator

The generator produces Python modules for each AWS service by combining:

1. **CloudFormation Resource Specification** - Resource types, properties, structure
2. **Botocore Service Models** - Enum values for type-safe constants

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Code Generator                                 │
│                                                                          │
│  ┌──────────────────────┐         ┌──────────────────────┐              │
│  │  CloudFormation Spec │         │   Botocore Models    │              │
│  │                      │         │                      │              │
│  │  • Resource types    │         │  • Enum values       │              │
│  │  • Property types    │         │  • Shape definitions │              │
│  │  • Property specs    │         │  • 10,000+ enums     │              │
│  │  • Required fields   │         │                      │              │
│  └──────────┬───────────┘         └──────────┬───────────┘              │
│             │                                │                          │
│             └───────────────┬────────────────┘                          │
│                             ▼                                           │
│                    ┌────────────────┐                                   │
│                    │   generate.py  │                                   │
│                    └────────┬───────┘                                   │
│                             │                                           │
│                             ▼                                           │
│              ┌──────────────────────────┐                               │
│              │  Generated Python Module │                               │
│              │                          │                               │
│              │  • @dataclass classes    │                               │
│              │  • Type annotations      │                               │
│              │  • Enum classes          │                               │
│              └──────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### CloudFormation Spec

**Source:** `https://d1uauaxba7bl26.cloudfront.net/latest/gzip/CloudFormationResourceSpecification.json`

The spec defines:

```json
{
  "ResourceTypes": {
    "AWS::DynamoDB::Table": {
      "Properties": {
        "TableName": {"PrimitiveType": "String", "Required": false},
        "KeySchema": {"Type": "List", "ItemType": "KeySchema", "Required": true}
      },
      "Attributes": {
        "Arn": {"PrimitiveType": "String"}
      }
    }
  },
  "PropertyTypes": {
    "AWS::DynamoDB::Table.KeySchema": {
      "Properties": {
        "AttributeName": {"PrimitiveType": "String", "Required": true},
        "KeyType": {"PrimitiveType": "String", "Required": true}
      }
    }
  }
}
```

### Botocore Enums

**Source:** Installed `botocore` package service models

Enum values extracted from shape definitions:

```python
# From dynamodb model
class KeyType:
    HASH = "HASH"
    RANGE = "RANGE"

class AttributeType:
    S = "S"
    N = "N"
    B = "B"
```

### Type Mapping

| Spec Type | Python Type |
|-----------|-------------|
| `PrimitiveType: String` | `str` |
| `PrimitiveType: Integer` | `int` |
| `PrimitiveType: Boolean` | `bool` |
| `PrimitiveType: Json` | `dict[str, Any]` |
| `Type: List` | `list[ItemType]` |
| `Type: Map` | `dict[str, ItemType]` |
| `Type: PropertyType` | `PropertyType` class |

### Generated Output

```python
"""
AWS DynamoDB CloudFormation resources.

Auto-generated from CloudFormation spec version X.X.X
Generator version: 1.0.0

DO NOT EDIT MANUALLY
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Union

from wetwire_aws.base import CloudFormationResource, PropertyType
from wetwire_aws.intrinsics.functions import Ref, GetAtt, Sub

# Enums from botocore
class KeyType:
    HASH = "HASH"
    RANGE = "RANGE"

class AttributeType:
    S = "S"
    N = "N"
    B = "B"

# Property types
@dataclass
class KeySchema(PropertyType):
    attribute_name: str
    key_type: Union[str, KeyType]

    def to_dict(self) -> dict[str, Any]:
        return {
            "AttributeName": self.attribute_name,
            "KeyType": self.key_type if isinstance(self.key_type, str) else self.key_type,
        }

# Resources
@dataclass
class Table(CloudFormationResource):
    _resource_type = "AWS::DynamoDB::Table"

    key_schema: list[KeySchema]
    attribute_definitions: list[AttributeDefinition]
    table_name: Optional[str] = None
    billing_mode: Optional[Union[str, BillingMode]] = None

    def to_dict(self) -> dict[str, Any]:
        # Serialization logic
        ...
```

### Regeneration

```bash
# Full regeneration
./scripts/regenerate.sh

# Specific service
python -m wetwire_aws.codegen.generate --service s3
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `src/wetwire_aws/decorator.py` | `@wetwire_aws` decorator, registry |
| `src/wetwire_aws/template.py` | `CloudFormationTemplate`, topological sort |
| `src/wetwire_aws/intrinsics/refs.py` | `ref()`, `get_att()`, `resolve_refs_from_annotations()` |
| `src/wetwire_aws/base.py` | `CloudFormationResource`, `PropertyType` base classes |
| `codegen/config.py` | Generator version, source URLs |
| `codegen/fetch.py` | Download CloudFormation spec |
| `codegen/parse.py` | Parse spec to intermediate format |
| `codegen/generate.py` | Generate Python classes |
| `codegen/extract_enums.py` | Extract botocore enums |

---

## See Also

- [Developer Guide](DEVELOPERS.md) - Development workflow
- [Versioning](VERSIONING.md) - Version management
- [CLI Reference](CLI.md) - CLI commands
