# Wetwire Python Implementation Plan

**Version:** 0.2
**Status:** Active
**Last Updated:** 2025-12-27

## Overview

This document describes the phased implementation of the Python wetwire packages, extracting and generalizing from the cloudformation_dataclasses proof-of-concept.

## Source Material

Reference POC: `cloudformation_dataclasses/`

| File | Contains |
|------|----------|
| `src/cloudformation_dataclasses/core/wrapper.py` | Decorator, Ref[T], GetAtt[T] |
| `src/cloudformation_dataclasses/core/registry.py` | ResourceRegistry |
| `src/cloudformation_dataclasses/core/template.py` | Template, Parameter, Output |
| `src/cloudformation_dataclasses/core/base.py` | CloudFormationResource, PropertyType |
| `src/cloudformation_dataclasses/intrinsics/` | CF intrinsic functions |
| `src/cloudformation_dataclasses/aws/` | Generated resource classes |

---

## Phase 1: graph-refs (Typing Library)

**Goal**: Standalone typing library with zero dependencies, suitable for stdlib consideration.

**Package**: `python/packages/graph-refs/`

### 1.1 Project Setup

- [ ] Create `python/packages/graph-refs/`
- [ ] Create `pyproject.toml` (hatchling build, no dependencies)
- [ ] Create `src/graph_refs/__init__.py`
- [ ] Create `src/graph_refs/py.typed`

### 1.2 Type Definitions (`_types.py`)

Extract and generalize from `wrapper.py`:

- [ ] `Ref[T]` - Generic type marker for references
- [ ] `Attr[T, name]` - Generic type for attribute references
- [ ] `RefList[T]` - Semantic alias for list[Ref[T]]
- [ ] `RefDict[K, V]` - Semantic alias for dict[K, Ref[V]]
- [ ] `ContextRef[name]` - Reference to context values

### 1.3 Introspection API (`_introspection.py`)

New implementation:

- [ ] `RefInfo` dataclass - Metadata about a reference field
- [ ] `get_refs(cls)` - Extract RefInfo from type hints
- [ ] `get_dependencies(cls, transitive=False)` - Compute dependency graph

### 1.4 Testing

- [ ] Unit tests for each type
- [ ] Type checker tests (mypy, pyright)
- [ ] Edge cases (forward refs, Optional, Union)

### 1.5 Documentation

- [ ] `README.md` with examples
- [ ] Docstrings for all public API

### 1.6 Deliverable

`pip install graph-refs` works, types work with mypy/pyright.

---

## Phase 2: wetwire (Core Framework)

**Goal**: Domain-agnostic framework that depends only on graph-refs.

**Package**: `python/packages/wetwire/`

### 2.1 Project Setup

- [ ] Create `python/packages/wetwire/`
- [ ] Create `pyproject.toml` (depends on graph-refs)
- [ ] Create package structure

### 2.2 Decorator (`decorator.py`)

Extract from `wrapper.py`, generalize:

- [ ] `@wetwire` decorator using `@dataclass_transform`
- [ ] Class reference detection (no-parens pattern)
- [ ] Attribute reference detection (`MyClass.Attr`)
- [ ] Collection processing (lists, dicts of references)

### 2.3 Registry (`registry.py`)

Extract from `registry.py`:

- [ ] `ResourceRegistry` class
- [ ] `register(cls, resource_type)` method
- [ ] `get_all(scope_package=None)` method
- [ ] `get_by_type(resource_type)` method
- [ ] Thread safety

### 2.4 Template (`template.py`)

Generalize from `template.py`:

- [ ] `Template` base class
- [ ] `from_registry(scope_package, context)` class method
- [ ] Abstract `to_dict()`, `to_json()`, `to_yaml()` methods
- [ ] `Parameter`, `Output` base classes

### 2.5 Provider (`provider.py`)

New abstraction:

- [ ] `Provider` ABC
- [ ] `serialize_ref(source, target)` abstract method
- [ ] `serialize_attr(source, target, attr)` abstract method
- [ ] `serialize_template(template)` abstract method

### 2.6 Context (`context.py`)

New implementation:

- [ ] `Context` base dataclass
- [ ] Context value resolution at serialization time

### 2.7 Helpers

- [ ] `computed.py` - `@computed` decorator for derived fields
- [ ] `conditions.py` - `when()`, `match()` conditional helpers

### 2.8 CLI Framework (`cli.py`)

Base CLI utilities for domain packages to extend:

- [ ] `discover_resources(module_path, registry)` - Import module to trigger registration
- [ ] `add_common_args(parser)` - Add standard CLI arguments (`--module`, `--scope`, `--verbose`)
- [ ] `create_list_command(registry, get_resource_type)` - Generic list command factory
- [ ] `create_validate_command(registry)` - Generic validate command factory

Common CLI arguments:
- `--module/-m` - Python module to import for resource discovery
- `--scope/-s` - Package scope to filter resources
- `--format/-f` - Output format (json/yaml)
- `--verbose/-v` - Verbose output

Domain packages extend this to create their specific CLIs:
- `wetwire-aws` → `wetwire-aws build/validate/list`
- `wetwire-k8s` → `wetwire-k8s build/validate/list`

### 2.9 Testing

- [ ] Unit tests for decorator behavior
- [ ] Integration tests for registry + template flow
- [ ] Type checker tests
- [ ] CLI utility tests

### 2.10 Deliverable

`pip install wetwire` works, can define resources without domain package.

---

## Phase 3: wetwire-aws (AWS Domain)

**Goal**: Full CloudFormation synthesis, migrating from cloudformation_dataclasses.

**Package**: `python/packages/wetwire-aws/`

### 3.1 Project Setup

- [ ] Create `python/packages/wetwire-aws/`
- [ ] Create `pyproject.toml` (depends on wetwire, pyyaml)
- [ ] Create package structure

### 3.2 Base Classes (`base.py`)

Move from `base.py`:

- [ ] `CloudFormationResource` base class
- [ ] `PropertyType` base class
- [ ] `_property_mappings` pattern
- [ ] `to_dict()` serialization

### 3.3 Intrinsics (`intrinsics/`)

Move from `intrinsics/`:

- [ ] `functions.py` - Ref, GetAtt, Sub, Join, If, Select, etc.
- [ ] `pseudo.py` - AWS_REGION, AWS_ACCOUNT_ID, AWS_STACK_NAME

### 3.4 Provider (`provider.py`)

New implementation:

- [ ] `CloudFormationProvider` implementing `Provider`
- [ ] CF-specific reference serialization (`{"Ref": ...}`)
- [ ] CF-specific attribute serialization (`{"Fn::GetAtt": ...}`)

### 3.5 Template (`template.py`)

Move from `template.py`:

- [ ] `CloudFormationTemplate` extending `Template`
- [ ] CF-specific sections (Parameters, Outputs, Conditions, Mappings)
- [ ] CF JSON/YAML serialization

### 3.6 Context (`context.py`)

New implementation:

- [ ] `AWSContext` with AWS pseudo-parameters
- [ ] Region, account_id, stack_name

### 3.7 Decorator (`decorator.py`)

Thin wrapper:

- [ ] `@wetwire_aws` - wraps `@wetwire` with AWS defaults

### 3.8 Resources (`resources/`)

Copy from `aws/`:

- [ ] All generated resource modules (s3/, ec2/, lambda_/, etc.)
- [ ] Update imports to use wetwire_aws

### 3.9 Linter (`linter/`)

Move from `linter/` if exists, or create:

- [ ] AWS-specific lint rules
- [ ] Security checks

### 3.10 CLI

Extends base CLI from wetwire core:

- [x] `wetwire-aws build` - Generate CloudFormation template (AWS-specific)
- [x] `wetwire-aws validate` - Validate references (uses base `create_validate_command`)
- [x] `wetwire-aws list` - List registered resources (uses base `create_list_command`)
- [ ] `wetwire-aws init` - Create new package
- [ ] `wetwire-aws lint` - Run linter

Refactor to use `wetwire.cli` utilities:
- [ ] Use `discover_resources()` from wetwire core
- [ ] Use `add_common_args()` from wetwire core
- [ ] Use `create_list_command()` and `create_validate_command()` factories

### 3.11 Testing

- [ ] Unit tests for intrinsics
- [ ] Integration tests for full stack generation
- [ ] Comparison tests against cloudformation_dataclasses output

### 3.12 Deliverable

`pip install wetwire-aws` works, generates valid CloudFormation.

---

## Validation Checkpoints

### After Phase 1

- [ ] `graph-refs` published to TestPyPI
- [ ] mypy and pyright pass on example code
- [ ] No runtime dependencies

### After Phase 2

- [ ] `wetwire` published to TestPyPI
- [ ] Can define a minimal resource class
- [ ] Registry correctly tracks resources
- [ ] Template base class works

### After Phase 3

- [ ] `wetwire-aws` published to TestPyPI
- [ ] Generated templates match cloudformation_dataclasses output
- [ ] AWS CloudFormation validates generated templates
- [ ] Agent workflow (`wetwire test`) passes simple prompts

---

## File Mapping: POC to Wetwire

| POC File | Target Package | Target File |
|----------|---------------|-------------|
| `core/wrapper.py` (types) | graph-refs | `_types.py` |
| `core/wrapper.py` (decorator) | wetwire | `decorator.py` |
| `core/registry.py` | wetwire | `registry.py` |
| `core/template.py` (base) | wetwire | `template.py` |
| `core/template.py` (CF) | wetwire-aws | `template.py` |
| `core/base.py` | wetwire-aws | `base.py` |
| `intrinsics/` | wetwire-aws | `intrinsics/` |
| `aws/` | wetwire-aws | `resources/` |

---

## Package Dependencies

```
graph-refs (no dependencies)
    │
    ▼
wetwire (depends: graph-refs)
    │
    ▼
wetwire-aws (depends: wetwire, pyyaml)
```

---

## Directory Structure (Final)

```
python/
├── pyproject.toml                    # Workspace root
└── packages/
    ├── graph-refs/
    │   ├── pyproject.toml
    │   ├── src/graph_refs/
    │   │   ├── __init__.py
    │   │   ├── py.typed
    │   │   ├── _types.py
    │   │   └── _introspection.py
    │   └── tests/
    │
    ├── wetwire/
    │   ├── pyproject.toml
    │   ├── src/wetwire/
    │   │   ├── __init__.py
    │   │   ├── py.typed
    │   │   ├── cli.py
    │   │   ├── computed.py
    │   │   ├── conditions.py
    │   │   ├── context.py
    │   │   ├── decorator.py
    │   │   ├── ordering.py
    │   │   ├── provider.py
    │   │   ├── registry.py
    │   │   └── template.py
    │   └── tests/
    │
    └── wetwire-aws/
        ├── pyproject.toml
        ├── src/wetwire_aws/
        │   ├── __init__.py
        │   ├── py.typed
        │   ├── base.py
        │   ├── decorator.py
        │   ├── template.py
        │   ├── provider.py
        │   ├── context.py
        │   ├── intrinsics/
        │   │   ├── __init__.py
        │   │   ├── functions.py
        │   │   └── pseudo.py
        │   ├── resources/
        │   │   ├── __init__.py
        │   │   ├── s3/
        │   │   ├── ec2/
        │   │   ├── lambda_/
        │   │   └── ...
        │   └── linter/
        └── tests/
```

---

## Success Criteria

### Phase 1 Complete When:
1. `graph-refs` is installable via pip
2. Type checkers recognize `Ref[T]` and `Attr[T, name]`
3. `get_refs()` correctly extracts reference metadata
4. Zero runtime dependencies

### Phase 2 Complete When:
1. `wetwire` is installable via pip
2. `@wetwire` decorator transforms classes correctly
3. Registry tracks all decorated classes
4. Template base class provides serialization hooks
5. CLI utilities available for domain packages to extend

### Phase 3 Complete When:
1. `wetwire-aws` is installable via pip
2. All cloudformation_dataclasses tests pass
3. Generated CF templates validate with AWS
4. CLI commands work (`init`, `lint`, `build`)

---

## Notes

- **No time estimates** - Focus on what, not when
- **Incremental delivery** - Each phase produces a usable package
- **Test-driven** - Write tests alongside implementation
- **Type-safe** - All code must pass mypy strict mode
