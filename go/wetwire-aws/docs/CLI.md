# CLI Reference

The `wetwire-aws` command provides tools for generating and validating CloudFormation templates from Go code.

## Quick Reference

| Command | Description |
|---------|-------------|
| `wetwire-aws build` | Generate CloudFormation template from Go source |
| `wetwire-aws lint` | Lint code for issues |
| `wetwire-aws init` | Initialize a new project |

```bash
wetwire-aws --help     # Show help
```

---

## build

Generate CloudFormation template from Go source files.

```bash
# Generate JSON to stdout
wetwire-aws build ./infra > template.json

# Generate YAML format
wetwire-aws build ./infra --format yaml > template.yaml

# With description
wetwire-aws build ./infra --description "My Application Stack"
```

### Options

| Option | Description |
|--------|-------------|
| `PATH` | Directory containing Go source files |
| `--format, -f {json,yaml}` | Output format (default: json) |
| `--description, -d TEXT` | Template description |

### How It Works

1. Parses Go source files using `go/ast`
2. Discovers `var X = Type{...}` resource declarations
3. Extracts resource dependencies from intrinsic references
4. Orders resources topologically by dependencies
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

## lint

Lint wetwire-aws code for issues.

```bash
# Lint a directory
wetwire-aws lint ./infra

# Lint a single file
wetwire-aws lint ./infra/storage.go
```

### Options

| Option | Description |
|--------|-------------|
| `PATH` | File or directory to lint |

### What It Checks

1. **Resource discovery**: Validates resources can be parsed from source
2. **Reference validity**: Checks that referenced resources exist
3. **Type correctness**: Validates resource types are valid CloudFormation types

### Output Examples

**Linting passed:**
```
Linting passed: 5 resources OK
```

**Issues found:**
```
./infra/storage.go:15: undefined resource reference: MissingBucket
./infra/compute.go:23: unknown resource type: AWS::Invalid::Type
```

---

## init

Initialize a new wetwire-aws project.

```bash
# Create a new project
wetwire-aws init -o myapp/
```

### Options

| Option | Description |
|--------|-------------|
| `-o, --output DIR` | Output directory (required) |

### Generated Structure

```
myapp/
├── go.mod
├── main.go
└── infra/
    └── storage.go
```

**main.go:**
```go
package main

import (
    "fmt"
    "myapp/infra"

    "github.com/lex00/wetwire-aws/internal/template"
)

func main() {
    t := template.New()
    t.Description = "My Application"
    // Add resources from infra package
    fmt.Println(t.ToJSON())
}
```

**infra/storage.go:**
```go
package infra

import "github.com/lex00/wetwire-aws/resources/s3"

var DataBucket = s3.Bucket{
    BucketName: "my-data-bucket",
}
```

---

## Typical Workflow

### Development

```bash
# Lint before generating
wetwire-aws lint ./infra

# Generate template
wetwire-aws build ./infra > template.json

# Preview YAML format
wetwire-aws build ./infra --format yaml
```

### CI/CD

```bash
#!/bin/bash
# ci.sh

# Lint first
wetwire-aws lint ./infra || exit 1

# Generate template
wetwire-aws build ./infra > template.json

# Deploy with AWS CLI
aws cloudformation deploy \
  --template-file template.json \
  --stack-name myapp \
  --capabilities CAPABILITY_IAM
```

---

## Intrinsic Functions

All CloudFormation intrinsic functions are supported:

| Function | Go API |
|----------|--------|
| Ref | `intrinsics.Ref{"LogicalId"}` |
| GetAtt | `intrinsics.GetAtt{"LogicalId", "Attr"}` |
| Sub | `intrinsics.Sub{"${AWS::StackName}-bucket"}` |
| SubWithMap | `intrinsics.SubWithMap{String: "...", Variables: map[string]any{...}}` |
| Join | `intrinsics.Join{",", []any{"a", "b"}}` |
| If | `intrinsics.If{"ConditionName", trueValue, falseValue}` |
| Equals | `intrinsics.Equals{value1, value2}` |
| And/Or/Not | `intrinsics.And{[]any{...}}`, `intrinsics.Or{...}`, `intrinsics.Not{...}` |
| FindInMap | `intrinsics.FindInMap{"MapName", "TopKey", "SecondKey"}` |
| Select | `intrinsics.Select{0, GetAZs{""}}` |
| Split | `intrinsics.Split{",", "a,b,c"}` |
| Base64 | `intrinsics.Base64{"Hello"}` |
| Cidr | `intrinsics.Cidr{"10.0.0.0/16", 256, 8}` |
| GetAZs | `intrinsics.GetAZs{"us-east-1"}` or `intrinsics.GetAZs{""}` |
| ImportValue | `intrinsics.ImportValue{"ExportedValue"}` |

---

## Pseudo-Parameters

Built-in CloudFormation pseudo-parameters:

```go
import "github.com/lex00/wetwire-aws/intrinsics"

// Available pseudo-parameters
intrinsics.AWS_REGION        // {"Ref": "AWS::Region"}
intrinsics.AWS_ACCOUNT_ID    // {"Ref": "AWS::AccountId"}
intrinsics.AWS_STACK_NAME    // {"Ref": "AWS::StackName"}
intrinsics.AWS_STACK_ID      // {"Ref": "AWS::StackId"}
intrinsics.AWS_PARTITION     // {"Ref": "AWS::Partition"}
intrinsics.AWS_URL_SUFFIX    // {"Ref": "AWS::URLSuffix"}
intrinsics.AWS_NO_VALUE      // {"Ref": "AWS::NoValue"}
```

Usage:
```go
var MyBucket = s3.Bucket{
    BucketName: intrinsics.Sub{"${AWS::StackName}-data"},
}
```

---

## See Also

- [Quick Start](QUICK_START.md) - Create your first project
- [Intrinsic Functions](INTRINSICS.md) - Full intrinsics reference
