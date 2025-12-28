# Comparison

A comparison of CloudFormation authoring approaches for teams evaluating their IaC tooling options.

## Who This Comparison Is For

Teams heavily invested in AWS who are at a crossroads with their infrastructure tooling. Common pain points:

- **Terraform**: State management overhead, team coordination around state locks, drift handling
- **CDK**: Node.js dependency, verbose generated templates, abstraction complexity
- **Raw CloudFormation**: Hostile authoring experience, no type safety, error-prone references
- **Corporate/opaque tooling**: Internal platforms that hide too much, vendor lock-in, "magic" that breaks

If you're happy with your current tooling, you probably don't need this library.

---

## Quick Summary

| Category | wetwire-aws | AWS CDK | Terraform |
|----------|-------------|---------|-----------|
| **Paradigm** | Declarative (Python) | Imperative (Python + Node.js) | Declarative (HCL) |
| **State management** | None (CloudFormation handles it) | Via CDK toolkit | Required (remote backend) |
| **Runtime** | Python only | Python + Node.js | Go binary |
| **Dependencies** | Minimal | 500MB+ | Terraform CLI + providers |
| **Learning curve** | Low | High | Medium |
| **Multi-cloud** | AWS only | AWS (primarily) | Multi-cloud |

---

## Syntax & Authoring

| Feature | wetwire-aws | AWS CDK | Terraform |
|---------|:-----------:|:-------:|:---------:|
| **Declarative syntax** | ✅ | ❌ | ✅ |
| Infrastructure defined as data | ✅ | ❌ | ✅ |
| No constructor/method calls | ✅ | ❌ | ✅ |
| No execution order dependencies | ✅ | ❌ | ✅ |
| Type-safe resource references | ✅ | ✅ | ❌ (strings) |
| IDE autocomplete | ✅ | ⚠️ | ⚠️ |
| Catch ref typos at edit time | ✅ | ⚠️ | ❌ |

### Syntax Comparison

```python
# wetwire-aws: Infrastructure as DATA
@wetwire_aws
class MyBucket:
    resource: Bucket
    bucket_name = "data"
    versioning: Annotated[MyVersioning, Ref()] = None  # Type-safe reference
```

```python
# CDK: Imperative construct tree
bucket = s3.Bucket(self, "MyBucket", bucket_name="data")
bucket.add_lifecycle_rule(...)  # Mutate after creation
```

```hcl
# Terraform: Declarative HCL
resource "aws_s3_bucket" "my_bucket" {
  bucket = "data"
}
```

Both wetwire-aws and Terraform are declarative. The difference: wetwire-aws uses Python with type hints and dataclass-dsl for introspection; Terraform uses HCL with state management.

---

## State Management

| Aspect | wetwire-aws | AWS CDK | Terraform |
|--------|:-----------:|:-------:|:---------:|
| **State file required** | ❌ | ❌ | ✅ |
| State locking concerns | N/A | N/A | Yes |
| Remote backend setup | N/A | N/A | Required for teams |
| Drift detection | Via CloudFormation | Via CDK | Via `terraform plan` |
| State contains secrets | N/A | N/A | Yes (plaintext) |

### The State Management Trade-off

Terraform's state file provides powerful features (resource tracking, drift detection, dependency graph). It also introduces operational overhead:

- **State locking**: Teams must coordinate who can run `terraform apply`
- **Remote backend**: S3 + DynamoDB (or similar) required for team use
- **Secrets exposure**: State files contain sensitive values in plaintext
- **State drift**: Discrepancies between state and reality require manual resolution

wetwire-aws delegates state entirely to CloudFormation. You author templates; CloudFormation tracks what's deployed. This is simpler but means you're tied to CloudFormation's capabilities.

---

## Runtime & Dependencies

| Feature | wetwire-aws | AWS CDK | Terraform |
|---------|:-----------:|:-------:|:---------:|
| **Pure Python** | ✅ | ❌ | N/A |
| No Node.js required | ✅ | ❌ | ✅ |
| Minimal transitive dependencies | ✅ | ❌ | ✅ |
| Python-only Docker images | ✅ | ❌ | N/A |

---

## CloudFormation Output

| Feature | wetwire-aws | AWS CDK |
|---------|:-----------:|:-------:|
| **Clean, minimal output** | ✅ | ❌ |
| No metadata in templates | ✅ | ❌ |
| Readable logical IDs | ✅ | ❌ (hashed) |
| 1:1 CloudFormation mapping | ✅ | ❌ |
| GitOps-friendly templates | ✅ | ⚠️ |

*Terraform generates its own plan format, not CloudFormation templates.*

### Output Comparison

**wetwire-aws:**
```json
{
  "Resources": {
    "MyBucket": {
      "Type": "AWS::S3::Bucket",
      "Properties": { "BucketName": "data" }
    }
  }
}
```

**AWS CDK:**
```json
{
  "Resources": {
    "MyBucketF68F3FF0": {
      "Type": "AWS::S3::Bucket",
      "Properties": { "BucketName": "data" },
      "Metadata": { "aws:cdk:path": "Stack/MyBucket/Resource" }
    }
  },
  "Parameters": { "BootstrapVersion": { ... } },
  "Rules": { "CheckBootstrapVersion": { ... } }
}
```

---

## Dependency Introspection

| Feature | wetwire-aws | AWS CDK | Terraform |
|---------|:-----------:|:-------:|:---------:|
| **Static dependency analysis** | ✅ | ⚠️ | ❌ |
| dataclass-dsl integration | ✅ | N/A | N/A |
| Topological ordering | ✅ | ✅ | ✅ |
| Dependency visualization | ✅ | ⚠️ | ✅ |

wetwire-aws uses dataclass-dsl for static dependency analysis:

```python
from typing import Annotated
from dataclass_dsl import Attr, get_dependencies

@wetwire_aws
class ProcessorFunction:
    resource: Function
    role: Annotated[str, Attr(ProcessorRole, "Arn")] = None  # Introspectable

# Get dependencies without instantiation
deps = get_dependencies(ProcessorFunction)
# Returns: {ProcessorRole}
```

---

## AI/Agent Friendliness

| Feature | wetwire-aws | AWS CDK | Terraform |
|---------|:-----------:|:-------:|:---------:|
| **Declarative = easier to generate** | ✅ | ❌ | ✅ |
| Simple class structure | ✅ | ❌ | ⚠️ |
| Type hints constrain output | ✅ | ⚠️ | ❌ |
| Predictable patterns | ✅ | ⚠️ | ✅ |
| No wiring/registration logic | ✅ | ❌ | ✅ |

AI assistants generate more reliable code with:
- **Declarative syntax**: No execution order to manage
- **Type hints**: Constraints that reduce the search space
- **Simple patterns**: Same structure for every resource

A Python dataclass with 5 typed fields is a better prompt than a 50-line YAML example.

---

## What Others Do Better

### CDK Strengths

| Feature | wetwire-aws | AWS CDK |
|---------|:-----------:|:-------:|
| L2/L3 high-level constructs | ❌ | ✅ |
| Asset bundling (Lambda zips) | ❌ | ✅ |
| Docker image building | ❌ | ✅ |
| Integrated deployment | ❌ | ✅ |
| Cross-stack references | ❌ | ✅ |

**Use CDK when you need**: High-level abstractions, asset bundling, or `cdk deploy` integration.

### Terraform Strengths

| Feature | wetwire-aws | Terraform |
|---------|:-----------:|:---------:|
| Multi-cloud support | ❌ | ✅ |
| Provider ecosystem | AWS only | Extensive |
| `terraform plan` preview | ❌ | ✅ |
| Import existing resources | ❌ | ✅ |

**Use Terraform when you need**: Multi-cloud infrastructure or non-AWS resources.

---

## Code Examples

### S3 Bucket with Encryption

**wetwire-aws:**
```python
from . import *

@wetwire_aws
class MyBucket:
    resource: s3.Bucket
    bucket_name = "my-app-data"
    bucket_encryption = {
        "ServerSideEncryptionConfiguration": [{
            "ServerSideEncryptionByDefault": {
                "SSEAlgorithm": s3.ServerSideEncryption.AES256
            }
        }]
    }
```

**AWS CDK:**
```python
bucket = s3.Bucket(
    self, "MyBucket",
    bucket_name="my-app-data",
    encryption=s3.BucketEncryption.S3_MANAGED,
)
```

CDK is more concise here—the L2 construct handles encryption configuration.

### Lambda with IAM Role

**wetwire-aws:**
```python
from . import *

@wetwire_aws
class MyRole:
    resource: iam.Role
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }
    managed_policy_arns = [
        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    ]

@wetwire_aws
class MyFunction:
    resource: lambda_.Function
    function_name = "my-handler"
    runtime = lambda_.Runtime.PYTHON3_12
    handler = "index.handler"
    role = get_att(MyRole, ARN)
```

**AWS CDK:**
```python
# CDK creates the role automatically
fn = lambda_.Function(
    self, "MyFunction",
    function_name="my-handler",
    runtime=lambda_.Runtime.PYTHON_3_12,
    handler="index.handler",
    code=lambda_.Code.from_asset("lambda"),  # Plus bundling
)
```

CDK is more concise and handles asset bundling. wetwire-aws is more explicit about what's created.

---

## When to Use wetwire-aws

- **AWS-only** infrastructure with no multi-cloud requirements
- Teams who want **no state management overhead**
- **Pure Python** environment (no Node.js)
- **Clean, readable** CloudFormation output
- **AI-assisted** infrastructure authoring
- **GitOps workflows** where templates are the source of truth
- **Dependency introspection** via dataclass-dsl

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Full support |
| ⚠️ | Partial/limited support |
| ❌ | Not supported |
| N/A | Not applicable |

---

## Notes

**Troposphere**: Another Python library for CloudFormation. Uses imperative syntax with string-based references. If you're considering Troposphere, wetwire-aws offers similar capabilities with type-safe references and declarative syntax plus dataclass-dsl integration.

---

## See Also

- [Quick Start](QUICK_START.md) - Get started with wetwire-aws
- [CLI Reference](CLI.md) - Build and validate commands
