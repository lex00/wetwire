# Internals

This document covers the internal architecture of wetwire-aws for contributors and maintainers.

**Contents:**
- [Resource Registry](#resource-registry) - How auto-registration works
- [Template Generation](#template-generation) - How templates are built
- [dataclass-dsl Integration](#dataclass-dsl-integration) - Dependency introspection
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
2. **Topologically sorts** resources by dependencies using dataclass-dsl
3. Resolves `Ref[T]` and `Attr[T, "name"]` annotations to intrinsics
4. Creates CloudFormation resource definitions

### Topological Sorting

Resources are ordered so dependencies come before dependents:

```python
from dataclass_dsl import get_dependencies

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

`resolve_refs_from_annotations()` converts dataclass-dsl types to CloudFormation intrinsics:

| dataclass-dsl Type | CloudFormation Output |
|--------------------|----------------------|
| `Annotated[MyBucket, Ref()]` | `{"Ref": "MyBucket"}` |
| `Annotated[str, Attr(MyRole, "Arn")]` | `{"Fn::GetAtt": ["MyRole", "Arn"]}` |
| `Annotated[str, ContextRef("AWS::Region")]` | `{"Ref": "AWS::Region"}` |
| `Annotated[list[MySecurityGroup], RefList()]` | (handled at value level) |

---

## dataclass-dsl Integration

wetwire-aws uses dataclass-dsl for dependency introspection and reference resolution.

### Type Annotations

```python
from typing import Annotated
from dataclass_dsl import Ref, Attr, ContextRef, RefList

@wetwire_aws
class MyFunction:
    resource: Function
    # These annotations enable introspection
    role: Annotated[str, Attr(MyRole, "Arn")] = None
    bucket: Annotated[MyBucket, Ref()] = None
    region: Annotated[str, ContextRef("AWS::Region")] = None
    security_groups: Annotated[list[SecurityGroup], RefList()] = None
```

### Introspection API

```python
from dataclass_dsl import get_refs, get_dependencies

# Get all references from a class
refs = get_refs(MyFunction)
# Returns: {"role": RefInfo(target=MyRole, attr="Arn"), ...}

# Get dependency classes
deps = get_dependencies(MyFunction)
# Returns: {MyRole, MyBucket}

# Transitive dependencies
all_deps = get_dependencies(MyFunction, transitive=True)
```

### Validation

The CLI uses dataclass-dsl to validate references:

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

The generator produces a service package with:
- `__init__.py` - Resources and enum constants
- `{resource}.py` - PropertyTypes for each resource (e.g., `table.py`)

**dynamodb/__init__.py** (resources and enums):
```python
"""AWS DYNAMODB CloudFormation resources."""

from wetwire_aws.base import CloudFormationResource, PropertyType, Tag
from . import table as _table  # Submodule alias

# Enums from botocore
class KeyType:
    HASH = "HASH"
    RANGE = "RANGE"

class ScalarAttributeType:
    S = "S"
    N = "N"
    B = "B"

# Resources reference PropertyTypes via submodule
@dataclass
class Table(CloudFormationResource):
    _resource_type: ClassVar[str] = "AWS::DynamoDB::Table"

    key_schema: list[_table.KeySchema] = field(default_factory=list)
    attribute_definitions: list[_table.AttributeDefinition] = field(default_factory=list)
    table_name: str | None = None
    billing_mode: str | None = None
```

**dynamodb/table.py** (PropertyTypes):
```python
"""PropertyTypes for AWS::DynamoDB::Table."""

from wetwire_aws.base import PropertyType

@dataclass
class KeySchema(PropertyType):
    attribute_name: str | None = None
    key_type: str | None = None

@dataclass
class AttributeDefinition(PropertyType):
    attribute_name: str | None = None
    attribute_type: str | None = None
```

**Usage:**
```python
from wetwire_aws.resources.dynamodb import Table, KeyType
from wetwire_aws.resources.dynamodb.table import KeySchema, AttributeDefinition

table = Table(
    key_schema=[KeySchema(attribute_name="pk", key_type=KeyType.HASH)],
    attribute_definitions=[AttributeDefinition(attribute_name="pk", attribute_type="S")],
)
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
