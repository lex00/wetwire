# CLI Reference

The `wetwire-aws` command provides tools for generating and validating CloudFormation templates.

## Quick Reference

| Command | Description |
|---------|-------------|
| `wetwire-aws build` | Generate CloudFormation template from registered resources |
| `wetwire-aws validate` | Validate resources and references |
| `wetwire-aws list` | List registered resources |
| `wetwire-aws lint` | Lint code for issues and auto-fix |
| `wetwire-aws import` | Import CloudFormation templates to Python |
| `wetwire-aws init` | Initialize a new project |

```bash
wetwire-aws --version  # Show version
wetwire-aws --help     # Show help
```

> **Note**: When developing with uv, prefix commands with `uv run`:
> ```bash
> uv run wetwire-aws build --module myapp.infra
> ```

---

## build

Generate CloudFormation template from registered resources.

```bash
# Generate JSON to stdout
wetwire-aws build --module myapp.infra > template.json

# Generate YAML format
wetwire-aws build --module myapp.infra --format yaml > template.yaml

# With description
wetwire-aws build --module myapp.infra --description "My Application Stack"

# Import multiple modules
wetwire-aws build --module myapp.network --module myapp.compute

# Scope to specific package
wetwire-aws build --module myapp --scope myapp.production
```

### Options

| Option | Description |
|--------|-------------|
| `--module, -m MODULE` | Python module to import for resource discovery (can be repeated) |
| `--scope, -s PACKAGE` | Package scope to filter resources |
| `--format, -f {json,yaml}` | Output format (default: json) |
| `--indent, -i N` | JSON indentation spaces (default: 2) |
| `--description, -d TEXT` | Template description |
| `--verbose, -v` | Verbose output |

### How It Works

1. Imports the specified module(s), which triggers resource registration
2. Resources auto-register with the global registry
3. Collects all registered resources (optionally filtered by scope)
4. Orders resources topologically by dependencies (using dataclass-dsl)
5. Generates CloudFormation JSON or YAML

### Output Modes

**JSON (default):**
```json
{
  "AWSTemplateFormatVersion": "2010-09-09",
  "Resources": {
    "DataBucket": {
      "Type": "AWS::S3::Bucket",
      "Properties": { "BucketName": "my-data" }
    }
  }
}
```

**YAML:**
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  DataBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: my-data
```

---

## validate

Validate resources and references without generating a template.

```bash
# Validate all resources
wetwire-aws validate --module myapp.infra

# Verbose output
wetwire-aws validate --module myapp.infra --verbose
```

### Options

| Option | Description |
|--------|-------------|
| `--module, -m MODULE` | Python module to import for resource discovery |
| `--scope, -s PACKAGE` | Package scope to filter resources |
| `--verbose, -v` | Verbose output |

### What It Checks

1. **Reference validity**: All `Annotated[T, Ref()]` and `Annotated[str, Attr(T, "name")]` targets exist in the registry
2. **Dependency graph**: Uses dataclass-dsl to compute and validate dependencies
3. **Registration**: Ensures all resources are properly decorated and registered

### Output Examples

**Validation passed:**
```
Validation passed: 5 resources OK
```

**With warnings:**
```
Validation passed with warnings:
  WARNING: MyBucket: Could not compute dependencies: ...
```

**Validation failed:**
```
Validation FAILED:
  ERROR: ProcessorFunction references MissingRole which is not registered
```

---

## list

List all registered resources.

```bash
# List resources from a module
wetwire-aws list --module myapp.infra

# Scope to specific package
wetwire-aws list --module myapp --scope myapp.production
```

### Options

| Option | Description |
|--------|-------------|
| `--module, -m MODULE` | Python module to import for resource discovery |
| `--scope, -s PACKAGE` | Package scope to filter resources |

### Output Example

```
Registered resources (3):

  DataBucket: AWS::S3::Bucket
  ProcessorFunction: AWS::Lambda::Function
  ProcessorRole: AWS::IAM::Role
```

---

## lint

Lint wetwire-aws code for issues and optionally auto-fix them.

```bash
# Lint a single file
wetwire-aws lint myapp/storage.py

# Lint a directory recursively
wetwire-aws lint myapp/

# Auto-fix issues
wetwire-aws lint myapp/ --fix

# Verbose output
wetwire-aws lint myapp/ --verbose
```

### Options

| Option | Description |
|--------|-------------|
| `PATH` | File or directory to lint |
| `--fix` | Auto-fix detected issues |
| `--verbose, -v` | Verbose output |

### Lint Rules

| Rule ID | Description | Auto-Fix |
|---------|-------------|:--------:|
| WAW001 | Use parameter type constants instead of string literals | ✅ |
| WAW002 | Use pseudo-parameter constants instead of `Ref("AWS::Region")` | ✅ |
| WAW003 | Use enum constants instead of string literals | ✅ |
| WAW004 | Use intrinsic function classes instead of raw dicts | ✅ |
| WAW005 | Remove unnecessary `.to_dict()` calls | ✅ |
| WAW006 | Use no-parens references instead of `ref()`/`get_att()` | ✅ |
| WAW007 | Use flat imports with module-qualified names | ✅ |
| WAW008 | Remove verbose imports handled by `setup_resources()` | ✅ |
| WAW010 | Split large files (>15 resources) into smaller files | ❌ |
| WAW011 | Use no-parens style for PropertyType wrappers (remove `()`) | ✅ |
| WAW012 | Detect duplicate resource class names | ❌ |
| WAW013 | Use wrapper classes instead of inline constructors | ❌ |
| WAW014 | Use wrapper classes instead of inline policy documents | ❌ |
| WAW015 | Use wrapper classes instead of inline security group rules | ❌ |
| WAW016 | Use wrapper classes instead of inline policy statements | ❌ |
| WAW017 | Use wrapper classes instead of inline property type dicts | ❌ |
| WAW018 | Remove redundant relative imports with `from . import *` | ❌ |

### Example: Auto-fixing Code

**Before:**
```python
type = "String"
region = Ref("AWS::Region")
vpc_id = ref(MyVPC)
role_arn = get_att(MyRole, "Arn")
```

**After `wetwire-aws lint --fix`:**
```python
type = STRING
region = AWS_REGION
vpc_id = MyVPC
role_arn = MyRole.Arn
```

### File Splitting Suggestions (WAW010)

When a file exceeds 15 resources, the linter suggests splitting by category. Resource categorization uses dynamic inference:

**Service-Based Categories:**

| Category | Services |
|----------|----------|
| storage | S3, EFS, FSx, Backup |
| compute | Lambda, EC2 (Instance, Volume, etc.), ECS, EKS |
| network | VPC, ElasticLoadBalancing, Route53, CloudFront |
| security | IAM, KMS, SecretsManager, WAF |
| database | RDS, DynamoDB, ElastiCache, Neptune |
| messaging | SNS, SQS, EventBridge |
| main | Everything else |

**EC2 Dynamic Categorization:**

EC2 resources are split between compute and network using keyword-based inference:

- **Network types**: Resources containing VPC, Subnet, Route, Gateway, Security, Network, Interface, Transit, Peering, EIP, VPN, Acl, DHCP, Endpoint, FlowLog, etc.
- **Compute types**: Resources containing Instance, Fleet, Host, Volume, KeyPair, Capacity, Snapshot, Enclave, LaunchTemplate, IPAM, Placement, etc.

This dynamic approach ensures new AWS resource types are categorized correctly without updating a static list.

---

## import

Import CloudFormation templates into wetwire-aws Python code.

```bash
# Import a template
wetwire-aws import template.yaml -o myapp/

# Import with custom package name
wetwire-aws import template.yaml -o myapp/ --name my_infra
```

See `wetwire-aws import --help` for all options.

---

## init

Initialize a new wetwire-aws project.

```bash
# Create a new project
wetwire-aws init -o myapp/
```

Creates a minimal project structure with `__init__.py`, `params.py`, and example resources.

---

## Typical Workflow

### Development

```bash
# List resources to verify registration
wetwire-aws list --module myapp.infra

# Validate before generating
wetwire-aws validate --module myapp.infra

# Generate template
wetwire-aws build --module myapp.infra > template.json

# Preview YAML format
wetwire-aws build --module myapp.infra --format yaml
```

### CI/CD

```bash
#!/bin/bash
# ci.sh

# Validate first
wetwire-aws validate --module myapp.infra || exit 1

# Generate template
wetwire-aws build --module myapp.infra > template.json

# Deploy with AWS CLI
aws cloudformation deploy \
  --template-file template.json \
  --stack-name myapp \
  --capabilities CAPABILITY_IAM
```

---

## Intrinsic Functions

All CloudFormation intrinsic functions are supported in resource definitions:

| Function | Python API |
|----------|------------|
| Ref | `Ref("LogicalId")` or `ref(MyResource)` |
| GetAtt | `GetAtt("LogicalId", "Attr")` or `get_att(MyResource, ARN)` |
| Sub | `Sub("${AWS::StackName}-bucket")` |
| Join | `Join("-", ["prefix", Ref("Suffix")])` |
| If | `If("ConditionName", true_value, false_value)` |
| Equals | `Equals(Ref("Env"), "prod")` |
| And/Or/Not | `And([cond1, cond2])`, `Or([...])`, `Not(cond)` |
| FindInMap | `FindInMap("MapName", "TopKey", "SecondKey")` |
| Select | `Select(0, GetAZs(""))` |
| Split | `Split(",", Ref("CommaSeparated"))` |
| Base64 | `Base64(Ref("UserData"))` |
| Cidr | `Cidr(Ref("VpcCidr"), 256, 8)` |
| GetAZs | `GetAZs(Ref("AWS::Region"))` |
| ImportValue | `ImportValue("ExportedValue")` |

---

## Pseudo-Parameters

Built-in CloudFormation pseudo-parameters:

```python
from wetwire_aws import (
    AWS_REGION,
    AWS_STACK_NAME,
    AWS_ACCOUNT_ID,
    AWS_PARTITION,
    AWS_STACK_ID,
    AWS_URL_SUFFIX,
    AWS_NO_VALUE,
    AWS_NOTIFICATION_ARNS,
)
```

Usage:
```python
class MyBucket:
    resource: Bucket
    bucket_name = Sub("${AWS::StackName}-data")
```

---

## Reference Type Annotations

Use type annotations for introspectable references:

```python
from typing import Annotated
from dataclass_dsl import Attr

class ProcessorFunction:
    resource: Function
    # Type annotation for introspection
    role: Annotated[str, Attr(ProcessorRole, "Arn")] = None
```

The CLI uses dataclass-dsl for:
- **Dependency detection**: `get_dependencies()` finds all referenced resources
- **Topological sorting**: Resources are ordered by dependencies in output
- **Validation**: Ensures all referenced resources exist

---

## See Also

- [Quick Start](QUICK_START.md) - Create your first project
- [Internals](INTERNALS.md) - How auto-registration works
- [Adoption Guide](ADOPTION.md) - Migration strategies
