# Quick Start

Get started with `wetwire-aws` in 5 minutes.

## Installation

```bash
# Using uv (recommended)
uv add wetwire-aws

# Or using pip
pip install wetwire-aws
```

## Your First Resource

Create a file `infra.py`:

```python
from wetwire_aws import wetwire_aws, CloudFormationTemplate
from wetwire_aws.resources.s3 import Bucket

@wetwire_aws
class DataBucket:
    resource: Bucket
    bucket_name = "my-data-bucket"

# Generate template
template = CloudFormationTemplate.from_registry()
print(template.to_json())
```

Run it:

```bash
python infra.py > template.json
```

That's it. Resources auto-register when the `@wetwire_aws` decorator is applied.

---

## Adding References

Reference other resources using `ref()` and `get_att()`:

```python
from wetwire_aws import wetwire_aws, CloudFormationTemplate, get_att, ARN
from wetwire_aws.resources.s3 import Bucket
from wetwire_aws.resources.iam import Role
from wetwire_aws.resources.lambda_ import Function, Runtime

@wetwire_aws
class DataBucket:
    resource: Bucket
    bucket_name = "data"

@wetwire_aws
class ProcessorRole:
    resource: Role
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
    resource: Function
    function_name = "processor"
    runtime = Runtime.PYTHON3_12
    handler = "index.handler"
    role = get_att(ProcessorRole, ARN)  # Reference to role

template = CloudFormationTemplate.from_registry()
print(template.to_yaml())
```

---

## Type-Safe References

For introspectable references, use type annotations:

```python
from wetwire import Ref, Attr
from wetwire_aws import wetwire_aws
from wetwire_aws.resources.lambda_ import Function, Runtime
from wetwire_aws.resources.iam import Role

@wetwire_aws
class ProcessorRole:
    resource: Role
    role_name = "processor"

@wetwire_aws
class ProcessorFunction:
    resource: Function
    function_name = "processor"
    runtime = Runtime.PYTHON3_12
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
wetwire-aws build --module infra > template.json

# Generate YAML
wetwire-aws build --module infra --format yaml

# List registered resources
wetwire-aws list --module infra

# Validate references
wetwire-aws validate --module infra
```

---

## Multi-File Organization

Split resources across files - they all register automatically:

```
myapp/
├── __init__.py      # Import all modules to trigger registration
├── storage.py       # S3, EFS
├── compute.py       # Lambda, EC2
├── network.py       # VPC, Subnets
└── database.py      # DynamoDB, RDS
```

**storage.py:**
```python
from wetwire_aws import wetwire_aws
from wetwire_aws.resources.s3 import Bucket

@wetwire_aws
class DataBucket:
    resource: Bucket
    bucket_name = "data"
```

**compute.py:**
```python
from wetwire import Ref
from wetwire_aws import wetwire_aws
from wetwire_aws.resources.lambda_ import Function, Runtime

# Import to access DataBucket
from .storage import DataBucket

@wetwire_aws
class ProcessorFunction:
    resource: Function
    function_name = "processor"
    runtime = Runtime.PYTHON3_12
    # Reference across files
    bucket: Ref[DataBucket] = None
```

**__init__.py:**
```python
# Import all modules to trigger registration
from . import storage
from . import compute
from . import network
from . import database
```

**Generate:**
```bash
wetwire-aws build --module myapp
```

---

## Type-Safe Constants

Use generated enum classes for type safety:

```python
from wetwire_aws.resources.lambda_ import Function, Runtime, Architecture
from wetwire_aws.resources.dynamodb import Table, KeyType, AttributeType

@wetwire_aws
class MyFunction:
    resource: Function
    runtime = Runtime.PYTHON3_12    # Not "python3.12"
    architectures = [Architecture.ARM64]

@wetwire_aws
class MyTable:
    resource: Table
    key_schema = [{"AttributeName": "pk", "KeyType": KeyType.HASH}]
    attribute_definitions = [
        {"AttributeName": "pk", "AttributeType": AttributeType.S}
    ]
```

---

## Template Building

`CloudFormationTemplate.from_registry()` collects all registered resources:

```python
from wetwire_aws import CloudFormationTemplate
from wetwire_aws.template import Parameter, Output

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

- See the full [CLI Reference](CLI.md)
- Learn about [migration strategies](ADOPTION.md)
- Understand [how it compares](COMPARISON.md) to CDK and Terraform
- Explore [internals](INTERNALS.md) for how auto-registration works
