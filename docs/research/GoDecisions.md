# Go Implementation Decisions

**Purpose:** Unblock parallel agent execution by documenting all human decisions upfront.
**Status:** DRAFT - Needs human review before agent work begins.

---

## Module Paths

```
github.com/lex00/wetwire-aws     # AWS domain package
github.com/lex00/wetwire-agent   # Agent CLI tool
```

**Decision needed:** Confirm org/repo naming.

---

## Directory Structure

```
wetwire-aws/
├── go.mod
├── go.sum
├── contracts.go              # All interfaces (Resource, Template, etc.)
├── internal/
│   ├── discover/             # AST parsing for var X = Type{...}
│   │   ├── discover.go
│   │   └── discover_test.go
│   ├── serialize/            # JSON/YAML serialization
│   │   ├── serialize.go
│   │   └── serialize_test.go
│   └── template/             # CloudFormation template building
│       ├── template.go
│       └── template_test.go
├── intrinsics/               # Public - Ref, GetAtt, Sub, etc.
│   ├── intrinsics.go
│   └── intrinsics_test.go
├── s3/                       # Generated
├── iam/                      # Generated
├── ec2/                      # Generated
├── lambda/                   # Generated
├── ...                       # ~260 service packages
├── codegen/                  # Code generator (not in published module)
│   ├── main.go
│   ├── fetch.go
│   ├── parse.go
│   └── generate.go
└── cmd/
    └── wetwire-aws/
        ├── main.go
        ├── build.go
        ├── lint.go
        └── validate.go

wetwire-agent/
├── go.mod
├── go.sum
├── internal/
│   ├── personas/
│   ├── scoring/
│   ├── results/
│   └── orchestrator/
└── cmd/
    └── wetwire-agent/
        ├── main.go
        ├── design.go
        ├── test.go
        └── scenario.go
```

---

## Interface Definitions (contracts.go)

```go
package wetwire_aws

// Resource represents a CloudFormation resource wrapper
type Resource interface {
    // ResourceType returns the CloudFormation type (e.g., "AWS::S3::Bucket")
    ResourceType() string

    // LogicalName returns the variable name used in user code
    LogicalName() string
}

// AttrRef represents a GetAtt reference (e.g., MyRole.Arn)
type AttrRef struct {
    Resource     string // Logical name of the resource
    Attribute    string // Attribute name (e.g., "Arn")
}

// MarshalJSON serializes to {"Fn::GetAtt": ["Resource", "Attr"]}
func (a AttrRef) MarshalJSON() ([]byte, error)

// Template represents a CloudFormation template
type Template struct {
    AWSTemplateFormatVersion string
    Description              string
    Resources                map[string]any
    Parameters               map[string]any
    Outputs                  map[string]any
}

// DiscoveredResource represents a resource found by AST parsing
type DiscoveredResource struct {
    Name         string            // Variable name (logical name)
    Type         string            // Go type (e.g., "iam.Role")
    Package      string            // Package path
    File         string            // Source file
    Line         int               // Line number
    Dependencies []string          // Other resources referenced
}

// BuildResult is the JSON output from `wetwire-aws build`
type BuildResult struct {
    Success   bool              `json:"success"`
    Template  map[string]any    `json:"template,omitempty"`
    Errors    []string          `json:"errors,omitempty"`
    Resources []string          `json:"resources,omitempty"`
}

// LintResult is the JSON output from `wetwire-aws lint`
type LintResult struct {
    Success bool        `json:"success"`
    Issues  []LintIssue `json:"issues,omitempty"`
}

type LintIssue struct {
    File     string `json:"file"`
    Line     int    `json:"line"`
    Column   int    `json:"column"`
    Severity string `json:"severity"` // "error", "warning", "info"
    Message  string `json:"message"`
    Rule     string `json:"rule"`
    Fixable  bool   `json:"fixable"`
}
```

---

## Generated Type Format

```go
// s3/bucket.go (generated)
package s3

import (
    wetwire "github.com/lex00/wetwire-aws"
)

// Bucket represents AWS::S3::Bucket
type Bucket struct {
    // Attrs (for GetAtt) - always present, populated by CLI at build time
    Arn                       wetwire.AttrRef
    DomainName                wetwire.AttrRef
    DualStackDomainName       wetwire.AttrRef
    RegionalDomainName        wetwire.AttrRef
    WebsiteURL                wetwire.AttrRef

    // Properties - user sets these
    BucketName                string
    VersioningConfiguration   *VersioningConfiguration
    Tags                      []Tag
    // ... all other properties
}

// ResourceType implements wetwire.Resource
func (b Bucket) ResourceType() string {
    return "AWS::S3::Bucket"
}

// LogicalName is set by the CLI during discovery
func (b Bucket) LogicalName() string {
    return b.logicalName
}

// Private field set by CLI
var _ wetwire.Resource = Bucket{}
```

**Decision needed:** How to store logical name? Options:
1. Private field set via reflection
2. Wrapper struct at build time
3. Separate registry map

---

## Optional Fields Strategy

**Decision:** Use pointers for optional fields, zero values for required.

```go
type Bucket struct {
    // Required - zero value is valid
    BucketName string

    // Optional - nil means not set
    VersioningConfiguration *VersioningConfiguration
    Tags                    []Tag  // Empty slice = not set
}
```

**Rationale:**
- Distinguishes "not set" from "set to empty string"
- Matches CloudFormation semantics
- Standard Go pattern

---

## Error Handling Style

**Decision:** Return errors, don't panic. Use wrapped errors.

```go
// Good
func Discover(path string) ([]DiscoveredResource, error) {
    if path == "" {
        return nil, fmt.Errorf("discover: path cannot be empty")
    }
    // ...
    if err != nil {
        return nil, fmt.Errorf("discover: parsing %s: %w", path, err)
    }
    return resources, nil
}

// Bad
func Discover(path string) []DiscoveredResource {
    if path == "" {
        panic("path cannot be empty")  // Don't do this
    }
}
```

---

## Naming Conventions

| CloudFormation | Go |
|----------------|-----|
| `BucketName` | `BucketName` (keep PascalCase) |
| `AWS::S3::Bucket` | `s3.Bucket` |
| `AWS::Lambda::Function` | `lambda.Function` (not `lambda_`) |
| `VPCId` | `VPCId` (preserve acronyms) |
| `Fn::GetAtt` | `AttrRef` struct |
| `Ref` | Direct variable reference |

**Package naming:**
- Use lowercase service name: `s3`, `iam`, `ec2`, `lambda`
- Reserved words: `lambda` is fine in Go (not a keyword)

---

## Test Strategy

**Decision:** Table-driven tests with golden files for serialization.

```go
func TestBucketSerialization(t *testing.T) {
    tests := []struct {
        name     string
        input    s3.Bucket
        wantJSON string
    }{
        {
            name: "simple bucket",
            input: s3.Bucket{
                BucketName: "my-bucket",
            },
            wantJSON: `{"Type":"AWS::S3::Bucket","Properties":{"BucketName":"my-bucket"}}`,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := json.Marshal(tt.input)
            require.NoError(t, err)
            assert.JSONEq(t, tt.wantJSON, string(got))
        })
    }
}
```

**Test dependencies:**
- `github.com/stretchr/testify` for assertions

---

## CLI JSON Contract

### `wetwire-aws build --output=json`

**Input:** Directory path containing Go files with resource declarations

**Output:**
```json
{
    "success": true,
    "template": {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "MyBucket": {
                "Type": "AWS::S3::Bucket",
                "Properties": {
                    "BucketName": "my-bucket"
                }
            }
        }
    },
    "resources": ["MyBucket", "MyRole"],
    "errors": []
}
```

**Exit codes:**
- 0: Success
- 1: Build error (invalid code, missing dependencies)
- 2: Validation error (invalid CloudFormation)

### `wetwire-aws lint --output=json`

**Output:**
```json
{
    "success": false,
    "issues": [
        {
            "file": "storage.go",
            "line": 15,
            "column": 4,
            "severity": "warning",
            "message": "BucketName should use a parameter or variable",
            "rule": "hardcoded-string",
            "fixable": true
        }
    ]
}
```

**Exit codes:**
- 0: No issues
- 1: Lint error (couldn't parse)
- 2: Issues found

---

## CF Spec → Go Type Mapping

| CF Type | Go Type |
|---------|---------|
| `String` | `string` |
| `Integer` | `int` |
| `Long` | `int64` |
| `Double` | `float64` |
| `Boolean` | `bool` |
| `Timestamp` | `string` (ISO 8601) |
| `Json` | `map[string]any` |
| `List` | `[]T` |
| `Map` | `map[string]T` |

**Property types:** Generate as nested structs in same package.

```go
// s3/bucket.go
type VersioningConfiguration struct {
    Status string // "Enabled" | "Suspended"
}
```

---

## Test Fixtures (Example User Code)

This code MUST compile and produce valid CloudFormation:

```go
// fixtures/simple/main.go
package main

import (
    "github.com/lex00/wetwire-aws/iam"
    "github.com/lex00/wetwire-aws/lambda"
    "github.com/lex00/wetwire-aws/s3"
)

var DataBucket = s3.Bucket{
    BucketName: "my-data-bucket",
}

var ProcessorRole = iam.Role{
    RoleName: "processor-role",
}

var ProcessorFunction = lambda.Function{
    FunctionName: "processor",
    Role:         ProcessorRole.Arn,  // GetAtt
    Environment: &lambda.Environment{
        Variables: map[string]string{
            "BUCKET": DataBucket.BucketName,  // Just the string value
        },
    },
}
```

**Expected output:**
```json
{
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "DataBucket": {
            "Type": "AWS::S3::Bucket",
            "Properties": {
                "BucketName": "my-data-bucket"
            }
        },
        "ProcessorRole": {
            "Type": "AWS::IAM::Role",
            "Properties": {
                "RoleName": "processor-role"
            }
        },
        "ProcessorFunction": {
            "Type": "AWS::Lambda::Function",
            "Properties": {
                "FunctionName": "processor",
                "Role": {"Fn::GetAtt": ["ProcessorRole", "Arn"]},
                "Environment": {
                    "Variables": {
                        "BUCKET": "my-data-bucket"
                    }
                }
            }
        }
    }
}
```

---

## Open Questions

1. **Logical name storage:** How does CLI set the logical name on discovered resources?
   - Option A: Reflection to set private field
   - Option B: Wrapper struct created at build time
   - Option C: Separate `map[any]string` registry

2. **Cross-file references:** How to handle `MyRole.Arn` when MyRole is in different file?
   - CLI parses all files, builds dependency graph, validates references

3. **Circular dependency detection:** How to report cycles?
   - Build error with cycle path: "A -> B -> C -> A"

4. **Enum generation:** Should enums be generated from botocore?
   - Option A: Yes, as string constants
   - Option B: No, just use strings

---

## Agent Assignment

Once decisions are finalized:

| Agent | Package | Files | Dependencies |
|-------|---------|-------|--------------|
| 1 | `internal/discover` | discover.go, discover_test.go | contracts.go |
| 2 | `internal/serialize` | serialize.go, serialize_test.go | contracts.go |
| 3 | `internal/template` | template.go, template_test.go | contracts.go |
| 4 | `intrinsics` | intrinsics.go, intrinsics_test.go | contracts.go |
| 5 | `codegen` | main.go, fetch.go, parse.go, generate.go | None |
| 6 | `cmd/wetwire-aws` | main.go, build.go, lint.go | All internal |
| 7 | `internal/personas` | personas.go, personas_test.go | None |
| 8 | `internal/scoring` | scoring.go, scoring_test.go | None |
| 9 | `internal/results` | results.go, results_test.go | None |
| 10 | `internal/orchestrator` | orchestrator.go, orchestrator_test.go | personas, scoring |
| 11 | AI integration | anthropic.go | orchestrator |
| 12 | `cmd/wetwire-agent` | main.go, design.go, test.go | All internal |

**Parallelization:**
- Agents 1-5, 7-9 can run simultaneously (no dependencies)
- Agent 6 waits for 1-5
- Agent 10 waits for 7-9
- Agents 11-12 wait for 10
