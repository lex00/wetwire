# Quick Start

Get started with `wetwire-aws` in 5 minutes.

## Installation

```bash
# Using uv (recommended)
uv add wetwire-aws

# Or using pip
pip install wetwire-aws
```

## Your First Project

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
```

**Generate template:**
```bash
wetwire-aws build --module myapp > template.json
```

That's it. Resources auto-register when the `@wetwire_aws` decorator is applied.

---

## Adding References

Reference other resources using `ref()` and `get_att()`:

**myapp/infra.py:**
```python
from . import *

@wetwire_aws
class DataBucket:
    resource: s3.Bucket
    bucket_name = "data"

@wetwire_aws
class ProcessorRole:
    resource: iam.Role
    role_name = "processor"
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
    function_name = "processor"
    runtime = lambda_.Runtime.PYTHON3_12
    handler = "index.handler"
    role = get_att(ProcessorRole, ARN)  # Reference to role
```

---

## Type-Safe References

For introspectable references, use type annotations:

```python
from . import *

@wetwire_aws
class ProcessorRole:
    resource: iam.Role
    role_name = "processor"

@wetwire_aws
class ProcessorFunction:
    resource: lambda_.Function
    function_name = "processor"
    runtime = lambda_.Runtime.PYTHON3_12
    # Type annotation enables dependency introspection
    role: Attr[ProcessorRole, "Arn"] = None
```

The annotation `Attr[ProcessorRole, "Arn"]` tells graph-refs this resource depends on `ProcessorRole` and uses its `Arn` attribute. This enables:

- Static dependency analysis
- Topological sorting in templates
- Validation of reference targets

---

## Using the CLI

```bash
# Generate template from a module
wetwire-aws build --module myapp > template.json

# Generate YAML
wetwire-aws build --module myapp --format yaml

# List registered resources
wetwire-aws list --module myapp

# Validate references
wetwire-aws validate --module myapp
```

---

## Multi-File Organization

Split resources across files:

```
myapp/
├── __init__.py      # Uses setup_resources() for auto-discovery
├── __init__.pyi     # Auto-generated for IDE support
├── storage.py       # S3, EFS
├── compute.py       # Lambda, EC2
├── network.py       # VPC, Subnets
└── database.py      # DynamoDB, RDS
```

**__init__.py** (the key file):
```python
from wetwire_aws.loader import setup_resources
setup_resources(__file__, __name__, globals())
```

`setup_resources()` automatically:
- Discovers all `.py` files in the package
- Parses them to find class definitions and references
- Loads modules in dependency order (dependencies first)
- Makes cross-file references work via namespace injection
- Generates `.pyi` stubs for IDE autocomplete

**storage.py:**
```python
from . import *

__all__ = ["DataBucket"]

@wetwire_aws
class DataBucket:
    resource: s3.Bucket
    bucket_name = "data"
```

**compute.py:**
```python
from . import *

__all__ = ["ProcessorFunction"]

@wetwire_aws
class ProcessorFunction:
    resource: lambda_.Function
    function_name = "processor"
    runtime = lambda_.Runtime.PYTHON3_12
    # Cross-file reference - DataBucket is injected by setup_resources()
    bucket: Ref[DataBucket] = None  # noqa: F821
```

**Generate:**
```bash
wetwire-aws build --module myapp
```

> **Note:** The `# noqa: F821` comment silences linter warnings about `DataBucket` being undefined. It's actually injected by `setup_resources()` before this module loads. The generated `.pyi` stub ensures IDE autocomplete still works.

---

## Type-Safe Constants

Use generated enum classes for type safety:

```python
from . import *

@wetwire_aws
class MyFunction:
    resource: lambda_.Function
    runtime = lambda_.Runtime.PYTHON3_12    # Not "python3.12"
    architectures = [lambda_.Architecture.ARM64]

@wetwire_aws
class MyTable:
    resource: dynamodb.Table
    key_schema = [{"AttributeName": "pk", "KeyType": dynamodb.KeyType.HASH}]
    attribute_definitions = [
        {"AttributeName": "pk", "AttributeType": dynamodb.ScalarAttributeType.S}
    ]
```

---

## Template Building

`CloudFormationTemplate.from_registry()` collects all registered resources:

```python
from myapp import CloudFormationTemplate

template = CloudFormationTemplate.from_registry(
    description="My Application Stack",
)

# Add parameters
template.add_parameter(
    "Environment",
    type="String",
    default="dev",
    allowed_values=["dev", "staging", "prod"],
)

# Add outputs
template.add_output(
    "BucketArn",
    value={"Fn::GetAtt": ["DataBucket", "Arn"]},
    description="Data bucket ARN",
)

print(template.to_json())
```

---

## Deploy

```bash
# Generate template
wetwire-aws build --module myapp > template.json

# Deploy with AWS CLI
aws cloudformation deploy \
  --template-file template.json \
  --stack-name myapp \
  --capabilities CAPABILITY_IAM
```

---

## Next Steps

- See the [Package Structure Guide](../../wetwire/docs/package-structure.md) for advanced multi-file patterns
- See the full [CLI Reference](CLI.md)
- Learn about [migration strategies](ADOPTION.md)
- Understand [how it compares](COMPARISON.md) to CDK and Terraform
- Explore [internals](INTERNALS.md) for how auto-registration works
