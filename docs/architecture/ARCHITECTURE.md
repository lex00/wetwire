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
│   ├── docs/               # Python-specific docs
│   └── packages/
│       ├── graph-refs/     # Typing library
│       ├── wetwire/        # Core framework
│       ├── wetwire-aws/    # AWS domain
│       ├── wetwire-gcp/    # GCP domain
│       └── wetwire-codegen/# Code generation
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
                         │    graph-refs      │
                         │  (typing library)  │
                         │  No dependencies   │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │     wetwire        │
                         │  (core framework)  │
                         │ depends: graph-refs│
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
| `graph-refs` | Typed references (`Ref[T]`, `Attr[T]`) | None (stdlib only) |
| `wetwire` | Core framework (decorator, registry, template) | `graph-refs` |
| `wetwire-aws` | AWS CloudFormation synthesis | `wetwire`, `pyyaml` |
| `wetwire-gcp` | GCP Config Connector synthesis | `wetwire`, `pyyaml` |
| `wetwire-azure` | Azure ARM synthesis | `wetwire`, `pyyaml` |
| `wetwire-k8s` | Kubernetes manifest synthesis | `wetwire`, `pyyaml` |
| `wetwire-actions` | GitHub Actions workflow synthesis | `wetwire`, `pyyaml` |
| `wetwire-codegen` | Code generation from schemas | Build-time only |

---

## Layer Architecture

### Layer 1: Typing Primitives (graph-refs)

General-purpose typed references for dataclass-based DSLs.

```
class Subnet:
    network: Ref[Network]          # Reference to Network
    gateway: Attr[Gateway, "Arn"]  # Attribute reference
```

**Key Components:**
- `Ref[T]` — Type marker for references
- `Attr[T, name]` — Type marker for attribute references
- `get_refs(class)` — Introspection API
- `get_dependencies(class)` — Dependency graph computation

### Layer 2: Core Framework (wetwire)

Domain-agnostic infrastructure for the declarative pattern.

```
@wetwire
class MyResource:
    resource: SomeType
    name = "example"
    related = OtherResource  # Auto-detected as reference
```

**Key Components:**
- `@wetwire` — Decorator that transforms classes
- `Registry` — Resource registration and discovery
- `Template` — Aggregation and serialization base
- `Provider` — Abstract interface for output formats
- `Context` — Environment values resolved at serialization

### Layer 3: Domain Packages (wetwire-aws, etc.)

Cloud-specific implementations with pre-generated resources.

```
@wetwire_aws
class MyBucket:
    resource: Bucket
    bucket_name = "data"
    encryption = AES256
```

**Key Components:**
- Domain decorator (`@wetwire_aws`)
- Domain template (`CloudFormationTemplate`)
- Domain context (`AWSContext` with pseudo-parameters)
- Domain provider (`CloudFormationProvider`)
- Generated resources (from cloud provider schemas)
- Intrinsic functions (domain-specific)

---

## Core Concepts

### The Wrapper Pattern

Every resource is a user-defined class wrapping a domain type:

```
@wetwire_aws
class MyDatabase:
    resource: RDSInstance      # The underlying type
    instance_class = "db.t3.micro"
    storage_size = 100
    encryption = Enabled
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
- [GRAPH_REFS_SPEC.md](../spec/GRAPH_REFS_SPEC.md) — Typing primitives specification

### Language-Specific Documentation

- Python: [python/docs/IMPLEMENTATION_PLAN.md](../../python/docs/IMPLEMENTATION_PLAN.md)
