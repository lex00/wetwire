# wetwire-aws

AWS CloudFormation synthesis for the wetwire framework.

## Installation

```bash
pip install wetwire-aws
```

## Quick Start

Create a package for your infrastructure:

```
myapp/
├── __init__.py
└── infra.py
```

**myapp/__init__.py:**
```python
from wetwire_aws.loader import setup_resources

# Magic: this single call injects into this package's namespace:
# - @wetwire_aws decorator
# - All resource modules: s3, iam, lambda_, ec2, dynamodb, sqs, sns, ...
# - Intrinsic helpers: ref, get_att, Sub, Join, If, ...
# - Attribute constants: ARN, ...
# - CloudFormationTemplate
setup_resources(__file__, __name__, globals())
```

**myapp/infra.py:**
```python
from . import *  # Everything you need, injected by setup_resources

@wetwire_aws
class MyVPC:
    resource: ec2.VPC
    cidr_block = "10.0.0.0/16"
    enable_dns_hostnames = True

@wetwire_aws
class WebSubnet:
    resource: ec2.Subnet
    vpc_id = MyVPC                     # Reference — no parens, no strings
    cidr_block = "10.0.1.0/24"
    availability_zone = "us-east-1a"

@wetwire_aws
class WebServer:
    resource: ec2.Instance
    subnet_id = WebSubnet              # Another reference
    instance_type = "t3.medium"
    image_id = "ami-12345678"
```

**Generate template:**
```python
from myapp import CloudFormationTemplate

template = CloudFormationTemplate.from_registry()
print(template.to_yaml())
```

## CLI Usage

```bash
# Generate CloudFormation JSON to stdout
wetwire-aws build --module myapp.infra > template.json

# Generate YAML format
wetwire-aws build --module myapp.infra --format yaml

# List registered resources
wetwire-aws list --module myapp.infra

# Validate resources and references
wetwire-aws validate --module myapp.infra
```

## Development

This package generates AWS CloudFormation resource classes at build time from
the official CloudFormation specification. The generated code is not stored in
the repository.

### First-Time Setup

After cloning, run the setup script to generate resources:

```bash
cd python/packages/wetwire-aws

# Create virtual environment
uv venv
source .venv/bin/activate

# Install with dev dependencies
uv sync --group dev --group codegen

# Generate resources
./scripts/dev-setup.sh
```

### Regenerating Resources

To regenerate after CloudFormation spec updates:

```bash
./scripts/regenerate.sh --force
```

### Building

The build process automatically runs codegen:

```bash
pip install hatch
hatch build  # Generates resources, then builds wheel/sdist
```

To skip codegen if resources already exist:

```bash
WETWIRE_SKIP_CODEGEN=1 hatch build
```

### Running Tests

```bash
uv run pytest
```

## License

Apache 2.0
