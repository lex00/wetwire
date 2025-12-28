# CLI Reference

The `wetwire-aws` command provides tools for generating and validating CloudFormation templates.

## Quick Reference

| Command | Description |
|---------|-------------|
| `wetwire-aws build` | Generate CloudFormation template from registered resources |
| `wetwire-aws validate` | Validate resources and references |
| `wetwire-aws list` | List registered resources |

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

1. Imports the specified module(s), which triggers `@wetwire_aws` decorators
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
@wetwire_aws
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

@wetwire_aws
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
