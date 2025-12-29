# Wetwire Architecture

**Version:** 0.1
**Status:** Draft
**Last Updated:** 2024-12-26

## Overview

Wetwire is a unified framework for declarative infrastructure-as-code using native language constructs. This document describes the overall system architecture, with Python as the first implementation language.

## Vision

Infrastructure code that is:
- **Flat** — No unnecessary nesting or constructor calls
- **Type-safe** — Full IDE support and static analysis
- **Readable** — By both humans and AI agents
- **Multi-cloud** — Same pattern across AWS, GCP, Azure, Kubernetes

## Repository Structure

```
wetwire/
├── docs/                    # Documentation (language-agnostic)
│   ├── spec/               # Specifications
│   ├── architecture/       # Architecture docs
│   └── personas/           # Agent testing personas
│
├── python/                  # Python implementation
│   └── packages/
│       └── wetwire-aws/    # AWS CloudFormation synthesis
│
├── go/                      # Go implementation (future)
├── rust/                    # Rust implementation (future)
├── typescript/              # TypeScript implementation (future)
│
└── examples/                # Example projects
```

---

## Package Architecture

### Dependency Graph

```
                         ┌────────────────────┐
                         │   dataclass-dsl    │
                         │  (typing library)  │
                         │  Published on PyPI │
                         └─────────┬──────────┘
                                   │
         ┌─────────────┬───────────┼───────────┬─────────────┐
         ▼             ▼           ▼           ▼             ▼
   ┌──────────┐  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
   │wetwire-  │  │wetwire-  │ │wetwire-  │ │wetwire-  │ │wetwire-  │
   │   aws    │  │   gcp    │ │  azure   │ │   k8s    │ │ actions  │
   └──────────┘  └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### Package Descriptions

| Package | Purpose | Dependencies |
|---------|---------|--------------|
| `dataclass-dsl` | Typed references and resource loading | None (stdlib only) |
| `wetwire-aws` | AWS CloudFormation synthesis | `dataclass-dsl`, `pyyaml` |
| `wetwire-gcp` | GCP Config Connector synthesis | `dataclass-dsl`, `pyyaml` (future) |
| `wetwire-azure` | Azure ARM synthesis | `dataclass-dsl`, `pyyaml` (future) |
| `wetwire-k8s` | Kubernetes manifest synthesis | `dataclass-dsl`, `pyyaml` (future) |
| `wetwire-actions` | GitHub Actions workflow synthesis | `dataclass-dsl`, `pyyaml` (future) |

---

## Layer Architecture

### Layer 1: Typing Primitives (dataclass-dsl)

General-purpose typed references for dataclass-based DSLs. Published as a standalone package on PyPI.

```python
class Subnet:
    network: Ref[Network]          # Reference to Network
    gateway: Attr[Gateway, "Arn"]  # Attribute reference
```

**Key Components:**
- `Ref[T]` — Type marker for references
- `Attr[T, name]` — Type marker for attribute references
- `get_refs(class)` — Introspection API
- `get_dependencies(class)` — Dependency graph computation

### Layer 2: Domain Packages (wetwire-aws, etc.)

Cloud-specific implementations with pre-generated resources.

```python
from . import *

@wetwire_aws
class MyBucket:
    resource: s3.Bucket
    bucket_name = "data"
    versioning_configuration = MyVersioning  # Reference to another wrapper

@wetwire_aws
class MyVersioning:
    resource: s3.bucket.VersioningConfiguration
    status = s3.BucketVersioningStatus.ENABLED
```

**Key Components:**
- Domain decorator (`@wetwire_aws`)
- Domain template (`CloudFormationTemplate`)
- Registry — Resource registration and discovery
- Generated resources (from cloud provider schemas)
- Intrinsic functions (`ref`, `get_att`, `Sub`, etc.)

---

## Core Concepts

### The Wrapper Pattern

Every resource is a user-defined class wrapping a domain type:

```python
from . import *

@wetwire_aws
class MyDatabase:
    resource: rds.DBInstance   # Module-qualified underlying type
    db_instance_class = "db.t3.micro"
    allocated_storage = 100
    storage_encrypted = True
```

### The No-Parens Principle

Resource relationships expressed without function calls:

```
# References are class names, not function calls
network = MyNetwork
role_arn = MyRole.Arn
subnets = [Subnet1, Subnet2]
```

### Auto-Registration

Decorated classes auto-register for discovery:

```
# All @wetwire classes are registered
template = Template.from_registry(scope_package="my_stack")
```

### Provider Abstraction

Same declaration, different output formats:

```
# CloudFormation JSON
cf_provider.serialize(template)  → {"Ref": "MyNetwork"}

# Kubernetes YAML
k8s_provider.serialize(template)  → name: my-network
```

---

## Data Flow

### Build-Time Flow

```
Cloud Schema (JSON/YAML)
         │
         ▼
  ┌─────────────┐
  │  Codegen    │  wetwire-codegen
  │  Parsers    │
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  Codegen    │
  │  Generators │
  └──────┬──────┘
         │
         ▼
Generated Resource Classes
(wetwire-aws/resources/s3/bucket.*)
```

### Runtime Flow

```
User Code (@wetwire classes)
         │
         ▼
  ┌─────────────┐
  │  Decorator  │  Reference detection, dataclass transform
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  Registry   │  Auto-registration
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  Template   │  Aggregation from registry
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  Provider   │  Format-specific serialization
  └──────┬──────┘
         │
         ▼
Output (JSON/YAML)
```

---

## Multi-Language Design

The pattern is language-agnostic. Each language implementation provides:

| Concept | Python | Go | Rust | TypeScript |
|---------|--------|-----|------|------------|
| Typed refs | `Ref[T]` | Interface | Trait | `Ref<T>` |
| Introspection | `get_type_hints()` | Reflect | Proc macro | Decorator |
| Decorator | `@wetwire` | Struct embedding | `#[wetwire]` | `@wetwire` |
| Codegen | Shared parsers | Language-specific generators |

---

## CLI Architecture

### Domain CLI Commands

Each domain package provides a CLI:

```bash
# AWS
wetwire-aws init my-stack       # Create new project
wetwire-aws lint                # Run linter
wetwire-aws build               # Generate template
wetwire-aws diff                # Show changes

# GCP
wetwire-gcp init my-stack
wetwire-gcp lint
wetwire-gcp build
```

### Core CLI Commands

The core `wetwire` CLI provides:

```bash
wetwire design --domain aws     # Interactive design with agent
wetwire test --domain aws       # Run agent tests
```

---

## Testing Architecture

### Unit Testing

Each package has unit tests in its respective `tests/` directory.

### Agent Testing

Agent-driven tests validate the complete workflow:

```
wetwire-aws/tests/agent/
├── prompts/
│   ├── simple.yaml
│   ├── medium.yaml
│   └── complex.yaml
├── baselines/
└── results/
```

See [AGENT_WORKFLOW.md](AGENT_WORKFLOW.md) for details.

---

## Security Considerations

### Design Principles

1. **Secure by default** — Encryption enabled, least privilege
2. **Lint for security** — Rules catch common misconfigurations
3. **No secrets in code** — Parameters and context for sensitive values

### Validation Points

1. **Static analysis** — Type checkers catch reference errors
2. **Linting** — Domain-specific security rules
3. **Template validation** — Cloud provider validates output

---

## Related Documents

- [AGENT_WORKFLOW.md](AGENT_WORKFLOW.md) — Agent testing and design workflow
- [CODEGEN_WORKFLOW.md](CODEGEN_WORKFLOW.md) — Schema fetching and code generation
- [WETWIRE_SPEC.md](../spec/WETWIRE_SPEC.md) — Pattern specification
