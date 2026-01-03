# Wetwire

Declarative infrastructure-as-code using native language constructs.

## Overview

Wetwire is a framework for defining cloud infrastructure using type-safe, flat declarations in Python and Go. It generates CloudFormation templates (AWS) with plans for GCP, Azure, and Kubernetes support.

**Key features:**
- **Flat declarations** — No unnecessary nesting or constructor calls
- **Type-safe** — Full IDE support and static analysis
- **AI-readable** — Designed for generation by LLM agents
- **Multi-language** — Same patterns in Python and Go

## Repositories

| Repository | Language | Description | Install |
|------------|----------|-------------|---------|
| [wetwire-core-python](https://github.com/lex00/wetwire-core-python) | Python | Core library (personas, scoring, agents) | `pip install wetwire-core` |
| [wetwire-aws-python](https://github.com/lex00/wetwire-aws-python) | Python | AWS CloudFormation synthesis | `pip install wetwire-aws` |
| [wetwire-core-go](https://github.com/lex00/wetwire-core-go) | Go | Core library (personas, scoring, agents) | `go get github.com/lex00/wetwire-core-go` |
| [wetwire-aws-go](https://github.com/lex00/wetwire-aws-go) | Go | AWS CloudFormation synthesis + CLI | `go get github.com/lex00/wetwire-aws-go` |

## Quick Example

### Python

```python
from wetwire_aws import *

class MyBucket:
    resource: s3.Bucket
    bucket_name = "my-data-bucket"

class MyRole:
    resource: iam.Role
    role_name = "processor-role"

class MyFunction:
    resource: lambda_.Function
    function_name = "processor"
    role = MyRole.Arn  # Type-safe reference
```

### Go

```go
var MyBucket = s3.Bucket{
    BucketName: "my-data-bucket",
}

var MyRole = iam.Role{
    RoleName: "processor-role",
}

var MyFunction = lambda.Function{
    FunctionName: "processor",
    Role:         MyRole.Arn, // Type-safe reference
}
```

## Documentation

This repository contains cross-language documentation:

- [Architecture](docs/architecture/ARCHITECTURE.md) — System design and patterns
- [Code Generation](docs/architecture/CODEGEN_WORKFLOW.md) — Schema fetching and code generation

### Research & Feasibility Studies

- [AWS](docs/research/AWS.md) — AWS CloudFormation patterns
- [Go Implementation](docs/research/Go.md) — Go-specific implementation details
- [GCP](docs/research/GCP.md) — GCP Config Connector feasibility
- [Azure](docs/research/AZURE.md) — Azure ARM feasibility
- [Kubernetes](docs/research/KUBERNETES.md) — Kubernetes manifest feasibility

## Status

| Domain | Python | Go |
|--------|--------|-----|
| AWS CloudFormation | ✅ Available | ✅ Available |
| Agent Framework | ✅ Available | 🚧 In progress |
| GCP Config Connector | 📋 Planned | 📋 Planned |
| Azure ARM | 📋 Planned | 📋 Planned |
| Kubernetes | 📋 Planned | 📋 Planned |

## License

MIT
