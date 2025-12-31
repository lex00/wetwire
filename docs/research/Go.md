# Wetwire Go Implementation

**Status**: Research complete
**Purpose**: Document Go ecosystem mappings, patterns, and architectural decisions for implementing wetwire in Go.
**Scope**: Go-specific design decisions; see `ImplementationChecklist.md` for feature matrix.
**Recommendation**: **Viable** - Direct type declaration, direct references.

---

## Executive Summary

Implementing wetwire in Go requires translating Python's dynamic "no parens" pattern to Go's static type system. The key insight: **`var X = Type{...}` - direct type, direct references**.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Python                              Go                                  │
│                                                                          │
│  class MyRole:                 →     var MyRole = iam.Role{             │
│      resource: iam.Role                  RoleName: "my-role",           │
│      role_name = "my-role"           }                                   │
│                                                                          │
│  role = MyRole.Arn             →     Role: MyRole.Arn                   │
│  bucket = MyBucket             →     Bucket: MyBucket                   │
│  MyRole.Arn                    →     MyRole.Arn                          │
│                                                                          │
│  Wrapper class + fields        →     Direct type declaration            │
│  ref()/get_att() helpers       →     Direct reference / dot access      │
│  Class attrs (.Arn)            →     Field access (.Arn)                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## GO ECOSYSTEM MAPPINGS

### CLI & Config Tools

| Concept | Go Library | Notes |
|---------|------------|-------|
| CLI framework | [cobra](https://github.com/spf13/cobra) | Industry standard, used by kubectl, gh, hugo |
| CLI flags | [pflag](https://github.com/spf13/pflag) | POSIX flags, integrates with cobra |
| Config files | [viper](https://github.com/spf13/viper) | Multi-format config, env vars, flags |
| Env vars | [envconfig](https://github.com/kelseyhightower/envconfig) | Struct tags for env binding |

### Code Generation

| Concept | Go Library | Notes |
|---------|------------|-------|
| Template engine | `text/template` | Stdlib, used for codegen |
| AST parsing | `go/ast`, `go/parser` | Stdlib for Go code analysis |
| Code formatting | `go/format` | Stdlib gofmt |
| Struct tags | `reflect` | Stdlib for tag extraction |
| Codegen tool | [jennifer](https://github.com/dave/jennifer) | Programmatic Go code generation |

### JSON/YAML/Serialization

| Concept | Go Library | Notes |
|---------|------------|-------|
| JSON | `encoding/json` | Stdlib |
| YAML | [gopkg.in/yaml.v3](https://github.com/go-yaml/yaml) | De facto standard |
| YAML (alt) | [sigs.k8s.io/yaml](https://github.com/kubernetes-sigs/yaml) | K8s-style, JSON-compatible |
| Struct mapping | [mapstructure](https://github.com/mitchellh/mapstructure) | Decode maps to structs |

### Type System

| Concept | Go Library | Notes |
|---------|------------|-------|
| Reflection | `reflect` | Detect types and references |
| Optional types | [mo](https://github.com/samber/mo) | Option, Result, Either monads |
| Validation | [validator](https://github.com/go-playground/validator) | Struct tag validation |
| Deep copy | [copier](https://github.com/jinzhu/copier) | Copy between structs |

### Dependency Ordering

| Concept | Go Library | Notes |
|---------|------------|-------|
| DAG/Topo sort | [gonum/graph](https://github.com/gonum/gonum) | Graph algorithms |
| DAG (simple) | [heimdalr/dag](https://github.com/heimdalr/dag) | Simple DAG implementation |

### AWS SDK & CloudFormation

| Concept | Go Library | Notes |
|---------|------------|-------|
| AWS SDK | [aws-sdk-go-v2](https://github.com/aws/aws-sdk-go-v2) | Official AWS SDK |
| CF spec | AWS SDK models | JSON specs in SDK |
| CF validation | [cfn-lint](https://github.com/aws-cloudformation/cfn-lint) | Python, call via exec |
| CF Go lib | [goformation](https://github.com/awslabs/goformation) | AWS Labs CF library |

### AI/LLM Integration

| Concept | Go Library | Notes |
|---------|------------|-------|
| Anthropic | [anthropic-sdk-go](https://github.com/anthropics/anthropic-sdk-go) | Official Anthropic SDK |
| OpenAI | [go-openai](https://github.com/sashabaranov/go-openai) | Community SDK |
| Streaming | Built into SDKs | SSE streaming support |

### Testing

| Concept | Go Library | Notes |
|---------|------------|-------|
| Testing | `testing` | Stdlib |
| Assertions | [testify](https://github.com/stretchr/testify) | Assert, require, mock |
| Golden files | [goldie](https://github.com/sebdah/goldie) | Snapshot testing |
| Table tests | Native | Go idiom with subtests |

### Linting

| Concept | Go Library | Notes |
|---------|------------|-------|
| Go linting | [golangci-lint](https://github.com/golangci/golangci-lint) | Meta-linter |
| AST linting | [analysis](https://pkg.go.dev/golang.org/x/tools/go/analysis) | Framework for analyzers |
| Custom rules | Write analyzers | Use analysis framework |

### Registry & Dependency Injection

| Concept | Go Library | Notes |
|---------|------------|-------|
| DI container | [wire](https://github.com/google/wire) | Compile-time DI |
| Service locator | [fx](https://github.com/uber-go/fx) | Runtime DI framework |
| Global registry | `sync.Map` or custom | Thread-safe map |

---

## EXISTING GO IaC LIBRARIES

| Library | Purpose | Relevance |
|---------|---------|-----------|
| [goformation](https://github.com/awslabs/goformation) | CloudFormation in Go | Direct competitor, study API |
| [pulumi-go](https://github.com/pulumi/pulumi/tree/master/sdk/go) | Pulumi Go SDK | Resource model patterns |
| [cdk8s-go](https://github.com/cdk8s-team/cdk8s) | K8s constructs in Go | Similar synthesis pattern |
| [terraform-plugin-sdk](https://github.com/hashicorp/terraform-plugin-sdk) | TF provider SDK | Schema patterns |

### goformation Deep-Dive

goformation (`github.com/awslabs/goformation`) is AWS Labs' Go library for CloudFormation. Understanding it deeply informs wetwire-go's design.

**Repository Status:** Archived October 2024. No new development.

#### goformation Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         goformation (AWS Labs)                           │
│                                                                          │
│   Template struct          Intrinsics              Resources             │
│   ├─ Resources map         ├─ Ref()               ├─ Auto-generated     │
│   ├─ Parameters            ├─ GetAtt()            ├─ From CF spec       │
│   ├─ Outputs               ├─ Sub()               ├─ 251+ services      │
│   └─ JSON()/YAML()         └─ Join(), If()...     └─ Typed structs      │
│                                                                          │
│   Usage Pattern:                                                         │
│   template := cloudformation.NewTemplate()                               │
│   template.Resources["MyBucket"] = &s3.Bucket{BucketName: String("x")}  │
│   json := template.JSON()                                                │
└─────────────────────────────────────────────────────────────────────────┘
```

#### What's USEFUL from goformation (Reusable Components)

| Component | Location | Usefulness | Reuse Strategy |
|-----------|----------|------------|----------------|
| **Intrinsic structs** | `intrinsics/` | High | Study patterns, don't copy (different serialization) |
| **Type conversion helpers** | `cloudformation/convert_types.go` | Medium | `String()`, `Int()`, `Bool()` pointer helpers |
| **CF spec processing** | `generate/` | Medium | Study code generation approach |
| **Template struct design** | `cloudformation/template.go` | Low | Different paradigm (imperative vs declarative) |
| **Resource struct patterns** | `cloudformation/resources/` | Low | Auto-generated, similar to wetwire |

**Specific goformation patterns to adopt:**

1. **Pointer Helper Functions:**
   ```go
   // goformation pattern - useful for optional fields
   func String(v string) *string { return &v }
   func Int(v int) *int { return &v }
   func Bool(v bool) *bool { return &v }
   ```

2. **Intrinsic Function Structs:**
   ```go
   // goformation: functions return map[string]interface{}
   func Ref(logicalName string) string {
       return fmt.Sprintf(`{"Ref":"%s"}`, logicalName)
   }
   ```

3. **Custom JSON Marshaling:**
   - goformation handles intrinsics in JSON output via string processing
   - wetwire should use proper MarshalJSON() on intrinsic types

#### What goformation CANNOT Do (wetwire's Value)

| Capability | goformation | wetwire | Benefit |
|------------|-------------|---------|---------|
| **Declarative wiring** | Imperative only | Wrapper pattern | All relationships declared in struct fields |
| **Cross-resource references** | String-based | Type-safe | `ref(MyVPC)` validates at compile time |
| **Dependency graph** | No analysis | Automatic | Topological sort from Ref/Attr analysis |
| **Multi-file packages** | Manual wiring | setup_resources() | Auto-discovery with dependency ordering |
| **AI-assisted generation** | None | wetwire-agent | Lint/build feedback loop |
| **Linting** | None | Built-in | Catch anti-patterns before build |
| **Template import** | Parsing only | Code generation | Import → wetwire code, not just structs |

#### Paradigm Comparison: No Parens vs Imperative

**goformation (Imperative - WITH Parens):**
```go
template := cloudformation.NewTemplate()

// Resources INSTANTIATED imperatively, added to map
bucket := &s3.Bucket{                              // ← Parens: instantiation
    BucketName: cloudformation.String("my-bucket"),
}
template.Resources["MyBucket"] = bucket            // ← String key, manual wiring

// Cross-references are STRINGS - no type safety
function := &lambda.Function{                      // ← Parens: instantiation
    Environment: &lambda.Function_Environment{
        Variables: map[string]string{
            "BUCKET": cloudformation.Ref("MyBucket"),  // ← String! Typos not caught
        },
    },
}
template.Resources["MyFunction"] = function        // ← Manual wiring
```

**wetwire (Declarative - Direct Type):**
```go
var MyBucket = s3.Bucket{
    BucketName: "my-bucket",
}

var MyFunction = lambda.Function{
    Bucket: MyBucket,  // Ref
}

// No init() - CLI discovers at build time
// $ wetwire build ./...

MyBucket.Arn  // ✓ Field on s3.Bucket
```

**The Key Difference:**
```go
// goformation: Ref("MyBucket") - string, error-prone
// wetwire:     MyBucket - type-safe

// goformation: template.Resources["name"] = &resource
// wetwire:     var MyBucket = s3.Bucket{...}
```

#### Why goformation's Approach Falls Short

1. **No Relationship Modeling:**
   - Resources are just map entries
   - No way to analyze dependencies
   - No topological sorting

2. **String-Based References:**
   - `Ref("MyBucket")` - typos not caught
   - No IDE autocomplete for resource names
   - No refactoring support

3. **No Package Organization:**
   - All resources in one file or manual imports
   - No multi-file dependency resolution
   - No namespace scoping

4. **No Validation Pipeline:**
   - No linting for anti-patterns
   - No build-time validation
   - No feedback for AI generation

#### goformation Code to NOT Copy

| Pattern | Why Avoid |
|---------|-----------|
| `template.Resources["name"] = &resource` | Imperative, no type safety |
| `intrinsics.Ref("string")` | String-based, error-prone |
| `json.MarshalIndent()` then string replace | Fragile intrinsic handling |
| Global `AllResources()` registry | Mutable global state |

#### Summary: Build vs Borrow

| Decision | Approach |
|----------|----------|
| **Template struct** | Build new (different paradigm) |
| **Intrinsic functions** | Build new (need MarshalJSON) |
| **Resource structs** | Generate from CF spec (like goformation) |
| **Type helpers** | Borrow pattern (`String()`, `Int()`, etc.) |
| **Reference system** | Build new (type-safe generics) |
| **Registry** | Build new (package-scoped) |
| **Dependency graph** | Build new (goformation has none) |

---

## THE "NO PARENS" PATTERN

The "no parens" pattern is wetwire's signature feature: **referencing types without instantiating them**. In Go, this translates to **flat struct values with direct references**.

### Python User Syntax

```python
class MyRole:
    resource: iam.Role
    role_name = "my-role"

class MyFunction:
    resource: lambda_.Function
    role = MyRole.Arn      # GetAtt via attribute access
    bucket = MyBucket      # Ref via naked class
```

### Go User Syntax

```go
// Generated resource types have all fields:
// type Role struct {
//     Arn      AttrRef
//     RoleName string
//     ...
// }

// User just declares and sets fields:
var MyRole = iam.Role{
    RoleName: "my-role",
}

var MyFunction = lambda.Function{
    FunctionName: "processor",
    Role:         MyRole.Arn,  // GetAtt
}

// No init() or Register() needed!
// CLI discovers resources at build time (like Python)

MyRole.Arn  // ✓ Field on iam.Role
```

**Key principles:**
- **Direct type** - `var X = Type{...}` (no wrapper needed)
- **Variable name** = logical resource name
- **Type** = CloudFormation resource type
- **No registration** - CLI discovers resources at build time
- **Resource name** for Ref (`MyBucket`), dot for GetAtt (`MyRole.Arn`)
- **No stubs needed** - Go's static typing gives IDE full support

### How It Works

**Generated resource types have all fields:**

```go
// iam/role.go (generated)
type Role struct {
    // Attrs - populated at build time
    Arn    AttrRef
    RoleId AttrRef

    // Properties - user sets these
    RoleName                 string
    AssumeRolePolicyDocument *PolicyDocument
}
```

**User declares with type, sets fields:**

```go
var MyRole = iam.Role{
    RoleName: "my-role",
}
```

**CLI discovers resources at build time (like Python):**

```bash
wetwire build ./...
```

The CLI:
1. Parses Go source files using `go/ast`
2. Finds `var X = <ResourceType>{...}` patterns
3. Extracts dependencies from resource references
4. Builds template in dependency order
5. Populates attr fields (Arn.Target, etc.)

**No init(), no Register(), no stubs** - just declare resources and build.

### Pattern Translation Table

| Python | Go | Serializes To |
|--------|-----|---------------|
| `MyRole` | `MyRole` | `{"Ref": "MyRole"}` |
| `MyRole.Arn` | `MyRole.Arn` | `{"Fn::GetAtt": ["MyRole", "Arn"]}` |
| `[MyStatement]` | `[]Statement{MyStatement}` | Array of Refs |

### Why This Works

1. **Flat**: No wrapper types, just struct values
2. **Idiomatic**: Direct field references, struct tags for metadata
3. **Type-safe**: `MyRole` is typed, `MyRole.Arn` is an AttrRef
4. **Dot syntax**: `MyRole.Arn` works because Arn is a field on the type
5. **Analyzable**: Framework detects resource vs attr by type

---

## GO-SPECIFIC IMPLEMENTATION NOTES

### 1. No Runtime Decorators or Registration
Python uses `@wetwire_aws` decorator. Go uses:
- Direct type declaration: `var X = Type{...}`
- CLI-based discovery at build time (like Python's `wetwire-aws build`)
- No init() or Register() calls needed

### 2. Declaration Pattern
```go
// Python: class MyRole:
//             resource: iam.Role
//             role_name = "my-role"

// Go: Direct type, set fields
var MyRole = iam.Role{
    RoleName: "my-role",
}
```

### 3. Reference Pattern
```go
// Python: role = MyRole.Arn
// Go: Dot access to attr field
var MyFunction = lambda.Function{
    Role: MyRole.Arn,  // GetAtt for Arn
}
```

### 4. Attr Access
```go
// Generated type has Arn, RoleId, RoleName, etc.
var MyRole = iam.Role{...}
MyRole.Arn       // ✓ Field on iam.Role
MyRole.RoleName  // ✓ Field on iam.Role
```

### 5. CLI Discovery (like Python)
```bash
wetwire build ./...
```

The CLI parses Go source using `go/ast`:
- Finds `var X = <ResourceType>{...}` patterns
- Extracts dependencies from resource references
- Builds template in dependency order

### 6. No Stubs Needed
Python needs `.pyi` stubs for IDE support (runtime injection).
Go doesn't - static types = IDE understands everything.

### 7. Go Keywords to Handle
```go
var GO_KEYWORDS = []string{
    "break", "case", "chan", "const", "continue", "default", "defer",
    "else", "fallthrough", "for", "func", "go", "goto", "if", "import",
    "interface", "map", "package", "range", "return", "select", "struct",
    "switch", "type", "var",
}
```

---

## SAMPLE GO PATTERNS

### Complete Example

```go
package myinfra

import (
    "wetwire/aws/iam"
    "wetwire/aws/lambda"
    "wetwire/aws/s3"
)

// Python: class DataBucket:
//             resource: s3.Bucket
//             bucket_name = "data"
var DataBucket = s3.Bucket{
    BucketName: "data",
}

// Python: class ProcessorRole:
//             resource: iam.Role
//             role_name = "processor-role"
var ProcessorRole = iam.Role{
    RoleName: "processor-role",
}

// Python: class ProcessorFunction:
//             resource: lambda_.Function
//             role = ProcessorRole.Arn
//             bucket = DataBucket
var ProcessorFunction = lambda.Function{
    FunctionName: "processor",
    Role:         ProcessorRole.Arn,
    Bucket:       DataBucket,
}

// No init() needed - just run: wetwire build ./...

// Usage:
// ProcessorRole.Arn  → GetAtt
// DataBucket         → Ref
```

### CLI Discovery (go/ast)

```go
// wetwire build parses source files to find resources
func discoverResources(pkg *ast.Package) []Resource {
    var resources []Resource

    for _, file := range pkg.Files {
        for _, decl := range file.Decls {
            if genDecl, ok := decl.(*ast.GenDecl); ok {
                for _, spec := range genDecl.Specs {
                    if valueSpec, ok := spec.(*ast.ValueSpec); ok {
                        // Look for: var X = <ResourceType>{...}
                        if isResourceDecl(valueSpec) {
                            resources = append(resources, extractResource(valueSpec))
                        }
                    }
                }
            }
        }
    }

    return resources
}
```

The CLI handles everything Python's decorator does:
- Discovers resources by parsing source
- Extracts dependencies from resource references
- Builds template in topological order

### Template Output

```go
template := wetwire.NewTemplate()
template.FromRegistry(registry)
json, _ := template.ToJSON()

// {
//   "Resources": {
//     "DataBucket": { "Type": "AWS::S3::Bucket", ... },
//     "ProcessorRole": { "Type": "AWS::IAM::Role", ... },
//     "ProcessorFunction": {
//       "Type": "AWS::Lambda::Function",
//       "Properties": {
//         "Role": {"Fn::GetAtt": ["ProcessorRole", "Arn"]},
//         ...
//       }
//     }
//   }
// }
```

### Slice of References

```go
// Python: statement = [AllowS3Access, AllowLogsWrite]
var MyPolicy = iam.PolicyDocument{
    Statement: []iam.Statement{
        AllowS3Access,
        AllowLogsWrite,
    },
}
```

---

## WETWIRE VS IaC LANDSCAPE

### Positioning in the IaC Ecosystem

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            IaC Tool Spectrum                                 │
│                                                                              │
│   LOW-LEVEL                                                    HIGH-LEVEL   │
│   (Templates)                                                  (Abstractions)│
│                                                                              │
│   CloudFormation    goformation    wetwire    CDK     Pulumi                │
│   (JSON/YAML)       (Go structs)   (Go decl)  (L2/L3) (Multi)               │
│        │                │              │         │        │                  │
│        ▼                ▼              ▼         ▼        ▼                  │
│   ┌─────────────────────────────────────────────────────────┐               │
│   │              Synthesis Layer (wetwire target)            │               │
│   │                                                          │               │
│   │  Typed structs → Serialization → Template JSON/YAML     │               │
│   └─────────────────────────────────────────────────────────┘               │
│        │                                                                     │
│        ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────┐               │
│   │           Deployment Layer (out of scope)                │               │
│   │                                                          │               │
│   │  aws cloudformation deploy / kubectl apply / az deploy  │               │
│   └─────────────────────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Detailed Comparison

| Aspect | CloudFormation | goformation | wetwire | AWS CDK | Pulumi |
|--------|----------------|-------------|---------|---------|--------|
| **Language** | YAML/JSON | Go | Go/Python | TS/Python/Go/Java | TS/Python/Go |
| **Paradigm** | Declarative | Imperative | Declarative | Imperative | Imperative |
| **Type Safety** | None | Struct-level | Field-level | L1: weak, L2: strong | Strong |
| **References** | Strings | Strings | Typed generics | Typed | Typed |
| **Dependencies** | Implicit | None | Automatic | Automatic | Automatic |
| **Multi-cloud** | No | No | Planned | No (AWS only) | Yes |
| **State** | CF service | N/A | N/A | CF service | Pulumi Cloud/self |
| **Deployment** | Native | N/A | N/A | CDK CLI | Pulumi CLI |
| **Linting** | cfn-lint | None | Built-in | CDK Aspects | None |
| **AI Integration** | None | None | wetwire-agent | None | Pulumi AI |
| **Scope** | Full IaC | Synthesis | Synthesis | Full IaC | Full IaC |

### What Makes wetwire Unique

**1. No Parens Pattern (Direct Type + Direct References)**

The core innovation is referencing resources without instantiation:

```go
// CDK/Pulumi/goformation: INSTANTIATE resources with parens
bucket := s3.NewBucket(stack, "MyBucket", &s3.BucketProps{...})
function := lambda.NewFunction(stack, "MyFunction", &lambda.FunctionProps{
    Environment: map[string]string{"BUCKET": bucket.BucketName()},
})

// wetwire: Direct type, set fields
var MyBucket = s3.Bucket{
    BucketName: "my-bucket",
}
var MyFunction = lambda.Function{
    Bucket: MyBucket,
}

MyBucket.Arn  // ✓ Field access, no method call
```

**Why this matters:**
| Imperative (CDK/Pulumi) | Declarative (wetwire) |
|-------------------------|----------------------|
| `bucket.BucketName()` | `MyBucket.Arn` |
| `s3.NewBucket(...)` | `s3.Bucket{...}` |
| Relationship via code flow | Relationship via references |
| Dependencies implicit | Dependencies extractable |

**2. Synthesis-Only (vs Full IaC)**
- CDK/Pulumi bundle deployment with synthesis
- wetwire generates templates; deployment is external
- Enables use with existing CI/CD, GitOps, etc.
- No vendor lock-in on deployment tooling

**3. AI-First Design**
- wetwire-agent provides lint feedback loop
- Designed for AI code generation from day one
- Personas enable systematic testing of AI behavior
- Scoring rubric enables CI quality gates

**4. Cross-Platform Synthesis**
- Same pattern for AWS, GCP, Azure, K8s
- Domain packages share wetwire-core patterns
- Agent workflow applies to all domains

### Why Not Use Existing Tools?

| Tool | Why Not | wetwire Alternative |
|------|---------|---------------------|
| **CDK** | AWS-only, complex L2/L3 abstractions | Multi-cloud, L1-equivalent with better DX |
| **Pulumi** | Requires Pulumi Cloud or backend | No state management, pure synthesis |
| **goformation** | Archived, imperative, no deps | Active, declarative, dependency graph |
| **Terraform** | HCL language, state management | Native Go, no state |

### Target Users

| User | Pain Point | wetwire Solution |
|------|------------|------------------|
| **Platform teams** | Need type-safe IaC generation | Typed Go structs with validation |
| **AI/LLM systems** | Need feedback loop for generation | Lint/build cycle with scoring |
| **Multi-cloud shops** | Different tools per cloud | Same pattern, different domain packages |
| **GitOps users** | Want templates, not deployment tools | Synthesis-only output |

---

## RECOMMENDED GO DEPENDENCIES

### Core (go.mod for wetwire-core)
```go
require (
    github.com/spf13/cobra v1.8.0        // CLI framework
    github.com/spf13/pflag v1.0.5        // POSIX flags
    gopkg.in/yaml.v3 v3.0.1              // YAML serialization
    gonum.org/v1/gonum v0.14.0           // Graph algorithms (topo sort)
)
```

### AWS Domain (go.mod for wetwire-aws)
```go
require (
    github.com/wetwire/wetwire-core v0.1.0
    github.com/aws/aws-sdk-go-v2 v1.24.0       // AWS SDK for codegen
    github.com/dave/jennifer v1.7.0            // Code generation
    github.com/stretchr/testify v1.8.4         // Testing
)
```

### Agent (go.mod for wetwire-agent)
```go
require (
    github.com/wetwire/wetwire-aws v0.1.0
    github.com/anthropics/anthropic-sdk-go v0.1.0  // Claude API
    github.com/spf13/cobra v1.8.0                   // CLI
)
```

### Build Tools
```bash
# Code generation
go install github.com/dave/jennifer/cmd/jennifer@latest

# Linting
go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

# Testing
go test -v ./...
```

---

## SOURCES

### Go IaC Libraries
- [goformation](https://github.com/awslabs/goformation) - AWS Labs CF library (archived 2024)
- [Pulumi Go SDK](https://github.com/pulumi/pulumi/tree/master/sdk/go) - Multi-cloud IaC
- [AWS CDK Go](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-go.html) - AWS CDK in Go
- [cdk8s](https://cdk8s.io/) - Kubernetes constructs

### IaC Comparisons
- [Pulumi vs CDK](https://www.pulumi.com/docs/iac/comparisons/cloud-template-transpilers/aws-cdk/) - Official Pulumi comparison
- [IaC Showdown](https://medium.com/@jasdeepsinghbhalla/%EF%B8%8F-infrastructure-as-code-showdown-aws-cdk-vs-terraform-vs-pulumi-vs-cloudformation-fc150a8c9f85) - CDK vs Terraform vs Pulumi
- [IaC Tools Comparison](https://www.naviteq.io/blog/choosing-the-right-infrastructure-as-code-tools-a-ctos-guide-to-terraform-pulumi-cdk-and-more/) - CTO's guide

### Go Ecosystem
- [Cobra](https://github.com/spf13/cobra) - CLI framework
- [gonum/graph](https://github.com/gonum/gonum) - Graph algorithms
- [jennifer](https://github.com/dave/jennifer) - Go code generation
- [anthropic-sdk-go](https://github.com/anthropics/anthropic-sdk-go) - Anthropic Go SDK
