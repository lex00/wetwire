# Wetwire

Declarative infrastructure-as-code using native language constructs.

## Vision

Infrastructure code that is:

- **Flat** — No unnecessary nesting or constructor calls
- **Type-safe** — Full IDE support and static analysis
- **Readable** — By both humans and AI agents
- **Multi-cloud** — Same pattern across AWS, GCP, Azure, Kubernetes

## The Pattern

```python
from . import *

@wetwire_aws
class MyVPC:
    resource: ec2.VPC
    cidr_block = "10.0.0.0/16"
    enable_dns_hostnames = True

@wetwire_aws
class WebSubnet:
    resource: ec2.Subnet
    vpc_id = MyVPC                 # Reference — no parens, no strings
    cidr_block = "10.0.1.0/24"
    availability_zone = "us-east-1a"

@wetwire_aws
class WebServer:
    resource: ec2.Instance
    subnet_id = WebSubnet          # Another reference
    instance_type = "t3.medium"
    image_id = "ami-12345678"
```

**Key insight**: References are class names, not function calls. The decorator detects them automatically.

## Packages

| Package | Purpose | Status |
|---------|---------|--------|
| `dataclass-dsl` | Typed references and resource loading | ✅ Published on PyPI |
| `wetwire-aws` | AWS CloudFormation synthesis | ✅ In Development |
| `wetwire-gcp` | GCP Config Connector synthesis | Future |
| `wetwire-azure` | Azure ARM synthesis | Future |
| `wetwire-k8s` | Kubernetes manifest synthesis | Future |
| `wetwire-actions` | GitHub Actions workflow synthesis | Future |

## Installation

```bash
# Not yet published — coming soon
pip install wetwire-aws
```

## Quick Example

```python
from . import *

@wetwire_aws
class DataBucket:
    resource: s3.Bucket
    bucket_name = "my-data-bucket"
    versioning_configuration = s3.bucket.VersioningConfiguration(
        status="Enabled"
    )

@wetwire_aws
class ProcessorFunction:
    resource: lambda_.Function
    function_name = "data-processor"
    runtime = lambda_.Runtime.PYTHON3_12
    handler = "index.handler"
    code = lambda_.function.Code(
        s3_bucket = DataBucket,            # No parens needed
        s3_key = "code.zip"
    )

# Generate CloudFormation template
template = CloudFormationTemplate.from_registry()
print(template.to_yaml())
```

Output:
```yaml
AWSTemplateFormatVersion: "2010-09-09"
Resources:
  DataBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: my-data-bucket
      VersioningConfiguration:
        Status: Enabled
  ProcessorFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: data-processor
      Runtime: python3.12
      Handler: index.handler
      Code:
        S3Bucket: {Ref: DataBucket}
        S3Key: code.zip
```

## Why Wetwire?

### vs. Raw CloudFormation/Terraform

- Type safety catches errors before deployment
- IDE autocompletion for all resource properties
- No YAML/HCL syntax to learn

### vs. CDK/Pulumi

- Flatter structure — no deep nesting of constructs
- No explicit `scope` or `id` parameters
- References are class names, not function calls
- Easier for AI agents to read and generate

### vs. Troposphere/AWS CDK (Python)

- Dataclass-based — familiar Python pattern
- No constructor calls for references
- Auto-registration eliminates manual wiring

## Architecture

```
┌────────────────────┐
│   dataclass-dsl    │  ← Typed references & resource loading
│  (no dependencies) │    Published on PyPI
└─────────┬──────────┘
          │
    ┌─────┼─────┬─────────┬─────────┐
    ▼     ▼     ▼         ▼         ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│ aws  │ │ gcp  │ │azure │ │ k8s  │ │actions│
└──────┘ └──────┘ └──────┘ └──────┘ └──────┘
```

## Multi-Language Support

The wetwire pattern is language-agnostic. This repository is structured to accommodate implementations in:

- **Python** (primary, in development)
- **Go** (future)
- **Rust** (future)
- **TypeScript** (future)

See [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) for details.

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) | System architecture |
| [AGENT_WORKFLOW.md](docs/architecture/AGENT_WORKFLOW.md) | Design and testing workflow |
| [IMPLEMENTATION_PLAN.md](docs/architecture/IMPLEMENTATION_PLAN.md) | Phased implementation roadmap |
| [WETWIRE_SPEC.md](docs/spec/WETWIRE_SPEC.md) | Pattern specification |
| [GRAPH_REFS_SPEC.md](docs/spec/GRAPH_REFS_SPEC.md) | Typing primitives specification |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 — see [LICENSE](LICENSE).

## Status

**Phase 0: Documentation**

We are currently in the documentation phase, establishing specifications before implementation. See [IMPLEMENTATION_PLAN.md](docs/architecture/IMPLEMENTATION_PLAN.md) for the roadmap.
