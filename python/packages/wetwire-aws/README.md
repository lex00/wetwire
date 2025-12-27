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
setup_resources(__file__, __name__, globals())
```

**myapp/infra.py:**
```python
from . import *

@wetwire_aws
class DataBucket:
    resource: s3.Bucket
    bucket_name = "my-data-bucket"
    versioning_configuration = {"Status": "Enabled"}

@wetwire_aws
class ProcessorRole:
    resource: iam.Role
    role_name = "data-processor"
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }

@wetwire_aws
class ProcessorFunction:
    resource: lambda_.Function
    function_name = "data-processor"
    runtime = lambda_.Runtime.PYTHON3_12  # Type-safe constants
    role = get_att(ProcessorRole, ARN)  # Reference to role ARN
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
