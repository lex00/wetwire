# Go Implementation Decisions

**Purpose:** Unblock parallel agent execution by documenting all human decisions upfront.
**Status:** DECISIONS COMPLETE - Ready for agent implementation.

---

## Module Paths

```
github.com/lex00/wetwire/go/wetwire-aws     # AWS domain package (library + CLI)
github.com/lex00/wetwire-agent   # Agent CLI tool (CLI only, not importable)
```

**Decision:** Module paths confirmed. Matches existing `lex00` GitHub organization.

---

## Directory Structure

```
go/wetwire-aws/
├── go.mod
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
│   ├── intrinsics_test.go
│   └── pseudo.go             # AWS pseudo-parameters
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
        └── init.go

go/wetwire-agent/
├── go.mod
├── internal/
│   ├── personas/             # Developer personas for testing
│   │   ├── personas.go
│   │   └── personas_test.go
│   ├── scoring/              # Rubric-based scoring
│   │   ├── scoring.go
│   │   └── scoring_test.go
│   ├── results/              # Session tracking and RESULTS.md
│   │   └── results.go
│   ├── orchestrator/         # Developer/Runner coordination
│   │   └── orchestrator.go
│   └── agents/               # Anthropic SDK integration
│       └── agents.go
└── cmd/
    └── wetwire-agent/
        ├── main.go
        ├── design.go
        ├── test.go
        ├── scenario.go
        └── list.go
```

---

## Interface Definitions (contracts.go)

```go
package wetwire_aws

// Resource represents a CloudFormation resource
type Resource interface {
    // ResourceType returns the CloudFormation type (e.g., "AWS::S3::Bucket")
    ResourceType() string
}

// Note: LogicalName is NOT part of the interface.
// CLI tracks logical names externally via map[string]DiscoveredResource.

// AttrRef represents a GetAtt reference (e.g., MyRole.Arn)
type AttrRef struct {
    Resource     string // Logical name of the resource
    Attribute    string // Attribute name (e.g., "Arn")
}

// MarshalJSON serializes to {"Fn::GetAtt": ["Resource", "Attr"]}
func (a AttrRef) MarshalJSON() ([]byte, error)

// IsZero returns true if the AttrRef has not been populated
func (a AttrRef) IsZero() bool

// Template represents a CloudFormation template (strongly typed)
type Template struct {
    AWSTemplateFormatVersion string                 `json:"AWSTemplateFormatVersion"`
    Description              string                 `json:"Description,omitempty"`
    Parameters               map[string]Parameter   `json:"Parameters,omitempty"`
    Resources                map[string]ResourceDef `json:"Resources"`
    Outputs                  map[string]Output      `json:"Outputs,omitempty"`
}

type ResourceDef struct {
    Type       string         `json:"Type"`
    Properties map[string]any `json:"Properties,omitempty"`
    DependsOn  []string       `json:"DependsOn,omitempty"`
}

type Parameter struct {
    Type          string   `json:"Type"`
    Description   string   `json:"Description,omitempty"`
    Default       any      `json:"Default,omitempty"`
    AllowedValues []string `json:"AllowedValues,omitempty"`
}

type Output struct {
    Description string `json:"Description,omitempty"`
    Value       any    `json:"Value"`
    Export      *struct {
        Name string `json:"Name"`
    } `json:"Export,omitempty"`
}

// DiscoveredResource represents a resource found by AST parsing
type DiscoveredResource struct {
    Name         string   // Variable name (logical name)
    Type         string   // Go type (e.g., "iam.Role")
    Package      string   // Package path
    File         string   // Source file
    Line         int      // Line number
    Dependencies []string // Other resources referenced
}

// BuildResult is the JSON output from `wetwire-aws build`
type BuildResult struct {
    Success   bool     `json:"success"`
    Template  Template `json:"template,omitempty"`
    Resources []string `json:"resources,omitempty"`
    Errors    []string `json:"errors,omitempty"`
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
    wetwire "github.com/lex00/wetwire/go/wetwire-aws"
)

// Bucket represents AWS::S3::Bucket
type Bucket struct {
    // Attrs (for GetAtt) - always present, zero values until CLI populates
    Arn                       wetwire.AttrRef `json:"-"`
    DomainName                wetwire.AttrRef `json:"-"`
    DualStackDomainName       wetwire.AttrRef `json:"-"`
    RegionalDomainName        wetwire.AttrRef `json:"-"`
    WebsiteURL                wetwire.AttrRef `json:"-"`

    // Properties - user sets these
    BucketName                string                   `json:"BucketName,omitempty"`
    VersioningConfiguration   *VersioningConfiguration `json:"VersioningConfiguration,omitempty"`
    Tags                      []Tag                    `json:"Tags,omitempty"`
    // ... all other properties
}

// ResourceType returns the CloudFormation type
func (b Bucket) ResourceType() string {
    return "AWS::S3::Bucket"
}
```

**Notes:**
- AttrRef fields have `json:"-"` - they're not serialized directly
- CLI uses separate `map[string]DiscoveredResource` for logical names (see Resolved Questions)
- No LogicalName() method needed - CLI tracks this externally

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
    "github.com/lex00/wetwire/go/wetwire-aws/iam"
    "github.com/lex00/wetwire/go/wetwire-aws/lambda"
    "github.com/lex00/wetwire/go/wetwire-aws/s3"
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

## User Project Structure

### `wetwire-aws init myproject`

Creates a new infrastructure project:

```
myproject/
├── go.mod                    # module myproject
├── main.go                   # Entry point (optional)
└── infra/
    ├── storage.go            # User resource definitions
    ├── compute.go
    └── network.go
```

### Import Requirements (Go vs Python)

**Python** provides a clean single-import experience:
```python
from . import *  # All AWS types available

class MyBucket:
    resource: s3.Bucket
    bucket_name = "my-bucket"
```

**Go** requires explicit imports per file (language limitation):
```go
package infra

import (
    "github.com/lex00/wetwire/go/wetwire-aws/s3"
    "github.com/lex00/wetwire/go/wetwire-aws/iam"
)

var MyBucket = s3.Bucket{
    BucketName: "my-bucket",
}
```

**Why Go is different:**
- Go's type system requires types to come from imported packages
- No runtime namespace manipulation like Python's `globals()`
- No wildcard imports that bring in module namespaces

**Mitigation:**
1. `wetwire-aws init` pre-populates common service imports (s3, iam, ec2, lambda, etc.)
2. Modern Go IDEs (gopls, GoLand) auto-add imports when you type a type name
3. The import block is at the top of the file, resource definitions remain clean

### Generated Starter File

`wetwire-aws init` generates `infra/resources.go`:

```go
package infra

import (
    // Common AWS services - add/remove as needed
    "github.com/lex00/wetwire/go/wetwire-aws/s3"
    "github.com/lex00/wetwire/go/wetwire-aws/iam"
    "github.com/lex00/wetwire/go/wetwire-aws/ec2"
    "github.com/lex00/wetwire/go/wetwire-aws/lambda"
    "github.com/lex00/wetwire/go/wetwire-aws/dynamodb"
    "github.com/lex00/wetwire/go/wetwire-aws/sqs"
    "github.com/lex00/wetwire/go/wetwire-aws/sns"
    "github.com/lex00/wetwire/go/wetwire-aws/apigateway"
)

// Define your infrastructure resources below

var _ = s3.Bucket{}     // Placeholder to prevent unused import errors
var _ = iam.Role{}      // Remove these as you add real resources
var _ = ec2.Instance{}
var _ = lambda.Function{}
```

### `wetwire-aws import template.yaml`

Imports existing CloudFormation template to Go:

```go
// Generated from template.yaml
package infra

import (
    "github.com/lex00/wetwire/go/wetwire-aws/s3"
    "github.com/lex00/wetwire/go/wetwire-aws/iam"
)

var MyBucket = s3.Bucket{
    BucketName: "imported-bucket",
    // ... all properties from template
}

var MyRole = iam.Role{
    RoleName: "imported-role",
    AssumeRolePolicyDocument: iam.PolicyDocument{
        // ... policy from template
    },
}
```

**Decision:** Imports are explicit but managed. Accept this as idiomatic Go rather than fighting the language.

---

## Resolved Questions

### 1. Logical Name Storage

**Decision: CLI-side map (no struct modification needed)**

The CLI discovers resources via AST parsing and already knows variable names. It maintains a `map[string]DiscoveredResource` keyed by logical name. During serialization, the CLI uses this map - no need to store the name on the struct itself.

```go
// internal/discover/discover.go
type DiscoveredResource struct {
    Name         string   // Variable name = logical name (e.g., "MyBucket")
    Type         string   // Go type (e.g., "s3.Bucket")
    File         string   // Source file
    Line         int      // Line number
    Dependencies []string // Referenced resources (e.g., ["MyRole"])
}

// CLI maintains: map[string]DiscoveredResource
// Key is the logical name, used during template serialization
```

**Rationale:**
- CLI already has this info from AST parsing
- No reflection or runtime modification needed
- Generated types stay simple (no private fields for metadata)

### 2. Cross-File References

**Decision: CLI parses all files in package, builds unified dependency graph**

```bash
wetwire-aws build ./infra/...
```

1. CLI discovers all `var X = Type{...}` declarations across all `.go` files in the package
2. For each resource, extracts field values that reference other resources (e.g., `MyRole.Arn`)
3. Builds dependency graph: `ProcessorFunction → ProcessorRole → DataBucket`
4. Validates all references resolve to discovered resources
5. Serializes in dependency order

**Error example:**
```
build error: infra/compute.go:15: ProcessorFunction references undefined resource "MyRole"
  hint: did you mean "ProcessorRole" (defined in infra/iam.go:8)?
```

### 3. Circular Dependency Detection

**Decision: Build error with full cycle path**

Uses Tarjan's SCC or Kahn's algorithm to detect cycles during topological sort.

**Error format:**
```
build error: circular dependency detected
  ProcessorFunction (infra/compute.go:15)
    → ProcessorRole (infra/iam.go:8)
    → DataBucket (infra/storage.go:5)
    → ProcessorFunction (infra/compute.go:15)
```

**Implementation:** `gonum.org/v1/gonum/graph/topo` provides cycle detection.

### 4. Enum Generation

**Decision: Generate typed string constants from botocore**

```go
// s3/enums.go (generated)
package s3

// BucketVersioningStatus represents valid values for VersioningConfiguration.Status
type BucketVersioningStatus string

const (
    BucketVersioningStatusEnabled   BucketVersioningStatus = "Enabled"
    BucketVersioningStatusSuspended BucketVersioningStatus = "Suspended"
)

// BucketAccelerateStatus represents valid values for AccelerateConfiguration.AccelerationStatus
type BucketAccelerateStatus string

const (
    BucketAccelerateStatusEnabled  BucketAccelerateStatus = "Enabled"
    BucketAccelerateStatusSuspended BucketAccelerateStatus = "Suspended"
)
```

**Usage in generated types:**
```go
type VersioningConfiguration struct {
    Status BucketVersioningStatus  // Typed for autocomplete
}
```

**User code:**
```go
var MyBucket = s3.Bucket{
    VersioningConfiguration: &s3.VersioningConfiguration{
        Status: s3.BucketVersioningStatusEnabled,  // IDE autocomplete
    },
}

// Also accepts raw strings (Go allows this)
var MyBucket2 = s3.Bucket{
    VersioningConfiguration: &s3.VersioningConfiguration{
        Status: "Enabled",  // Works but no autocomplete
    },
}
```

**Rationale:**
- IDE autocomplete for valid values
- Some compile-time safety (wrong type = error)
- Still accepts raw strings for flexibility
- Matches Python implementation's enum generation

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
