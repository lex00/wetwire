# wetwire-aws (Go)

Generate CloudFormation templates from Go resource declarations using a declarative, type-safe syntax.

## Status

**Implementation: In Progress**

See [Implementation Status](#implementation-status) for details.

## Quick Start

```go
package infra

import (
    "github.com/lex00/wetwire-aws/resources/s3"
    "github.com/lex00/wetwire-aws/resources/iam"
    "github.com/lex00/wetwire-aws/intrinsics"
)

// Direct type declaration - no wrappers, no registration
var DataBucket = s3.Bucket{
    BucketName: "my-data-bucket",
}

var ProcessorRole = iam.Role{
    RoleName: "processor-role",
}

var ProcessorFunction = lambda.Function{
    FunctionName: "processor",
    Role:         ProcessorRole.Arn,  // GetAtt via field access
    Environment: lambda.Environment{
        Variables: map[string]any{
            "BUCKET": intrinsics.Ref{"DataBucket"},
        },
    },
}
```

Generate template:

```bash
wetwire-aws build ./infra > template.json
```

## Installation

```bash
go install github.com/lex00/wetwire-aws/cmd/wetwire-aws@latest
```

## CLI Commands

| Command | Status | Description |
|---------|--------|-------------|
| `build` | ⚠️ Partial | Generate CloudFormation template |
| `lint` | ⚠️ Partial | Check for issues |
| `init` | ✅ Complete | Initialize new project |
| `import` | ✅ Complete | Import CF template to Go code |
| `validate` | ❌ Missing | Validate resources |
| `list` | ❌ Missing | List resources |

## Implementation Status

### What's Working

- **Intrinsic Functions**: All CloudFormation intrinsics (Ref, GetAtt, Sub, Join, etc.)
- **Pseudo-Parameters**: AWS_REGION, AWS_ACCOUNT_ID, AWS_STACK_NAME, etc.
- **AST Discovery**: Parse Go source to find resource declarations
- **Template Builder**: Build CF template with topological ordering
- **Cycle Detection**: Detect circular dependencies
- **JSON/YAML Output**: Serialize to CF template format
- **Code Generator**: Generate Go types from CloudFormation spec

### What's Missing

| Feature | Priority | Issue |
|---------|----------|-------|
| `build` value loading | **P0** | Currently uses empty placeholders |
| Full linter | P1 | Only checks discovery errors, no rules |
| `validate` command | P1 | Not implemented |
| `list` command | P1 | Not implemented |

### Known Issues

1. **Empty Properties in Build Output**

   The `build` command discovers resources but outputs empty properties.
   See TODO at `cmd/wetwire-aws/build.go:65-68`:

   ```go
   // TODO: Load actual resource values from compiled Go code
   // For now, we just use empty values as placeholder
   for name := range result.Resources {
       builder.SetValue(name, map[string]any{})
   }
   ```

## Package Structure

```
wetwire-aws/
├── cmd/wetwire-aws/       # CLI application
│   ├── main.go            # Entry point
│   ├── build.go           # build command
│   ├── lint.go            # lint command
│   ├── init.go            # init command
│   └── import.go          # import command
├── internal/
│   ├── discover/          # AST-based resource discovery
│   ├── importer/          # CloudFormation template importer
│   │   ├── ir.go          # Intermediate representation types
│   │   ├── parser.go      # YAML/JSON template parser
│   │   └── codegen.go     # Go code generator
│   ├── serialize/         # JSON/YAML serialization
│   └── template/          # Template builder with topo sort
├── intrinsics/
│   ├── intrinsics.go      # Ref, GetAtt, Sub, Join, etc.
│   └── pseudo.go          # AWS pseudo-parameters
├── codegen/               # Generate Go types from CF spec
│   ├── fetch.go           # Download CF spec
│   ├── parse.go           # Parse spec JSON
│   └── generate.go        # Generate Go files
├── contracts.go           # Core types (Resource, AttrRef, Template)
├── docs/
│   ├── QUICK_START.md
│   └── CLI.md
└── scripts/
    ├── ci.sh              # Local CI script
    └── import_aws_samples.sh  # Test against AWS samples
```

## Development

```bash
# Run tests
go test -v ./...

# Run CI checks
./scripts/ci.sh

# Build CLI
go build -o wetwire-aws ./cmd/wetwire-aws
```

## Documentation

- [Quick Start](docs/QUICK_START.md)
- [CLI Reference](docs/CLI.md)
- [Implementation Checklist](../../docs/research/ImplementationChecklist.md)
- [Go Design Decisions](../../docs/research/Go.md)

## Related Packages

- [wetwire-agent](../wetwire-agent/) - AI agent for infrastructure design
- [wetwire-aws (Python)](../../python/packages/wetwire-aws/) - Python implementation
