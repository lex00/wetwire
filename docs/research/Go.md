# Wetwire Go Implementation

**Status**: Research complete
**Purpose**: Document Go ecosystem mappings, patterns, and architectural decisions for implementing wetwire in Go.
**Scope**: Go-specific design decisions; see `ImplementationChecklist.md` for feature matrix.
**Recommendation**: **Viable** - Flat struct values with embedded attrs and pointer references.

---

## Executive Summary

Implementing wetwire in Go requires translating Python's dynamic "no parens" pattern to Go's static type system. The key insight: **Everything is flat, everything is a struct**. Resources are package-level struct values with embedded attrs, and references are just pointers.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Python                              Go                                  │
│                                                                          │
│  class MyRole:                 →     var MyRole = iam.Role{...}         │
│      resource: iam.Role                                                  │
│                                                                          │
│  role = MyRole.Arn             →     Role: &MyRole  (+ attr tag)        │
│  bucket = MyBucket             →     Bucket: &MyBucket                  │
│  MyRole.Arn (for external use) →     MyRole.Arn (field access)          │
│                                                                          │
│  Wrapper classes               →     Flat struct values                 │
│  ref()/get_att() helpers       →     Pointers + struct tags             │
│  Class attrs (.Arn)            →     Embedded attr fields               │
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
| Reflection | `reflect` | Detect pointer-to-wrapper fields |
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

**wetwire (Declarative - Embedded Types + Pointer References):**
```go
// Wrapper embeds resource type, declares properties
type myBucket struct {
    s3.Bucket           // Embedded - indicates resource type, promotes .Arn
    BucketName string
}

type myFunction struct {
    lambda.Function
    Bucket *s3.Bucket   // Pointer = reference (no parens on MyBucket!)
}

// Exported values - what users interact with
var MyBucket = myBucket{BucketName: "my-bucket"}
var MyFunction = myFunction{Bucket: &MyBucket.Bucket}

func init() {
    wetwire.Register(&MyBucket, &MyFunction)
}

// Attrs accessible via promotion:
MyBucket.Arn  // ✓ Promoted from embedded s3.Bucket
```

**The Key Difference:**
```go
// goformation: Ref("MyBucket") - string argument, loses type info
// wetwire:     &MyBucket.Bucket - pointer, type-safe, refactorable

// goformation: lambda.Function{...} - instantiate, add to map
// wetwire:     var MyFunction = myFunction{...} - declare once, reference by pointer
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

The "no parens" pattern is wetwire's signature feature: **referencing types without instantiating them**. In Go, this translates to **flat struct values with pointer references**.

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

### Go User Syntax: Embedded Resource Types

```go
// Wrapper struct with embedded resource type (like Python's resource: iam.Role)
type myRole struct {
    iam.Role
    RoleName string  // PascalCase matches CF property name
}

type myFunction struct {
    lambda.Function
    FunctionName string
    Role         *iam.Role `attr:"Arn"`  // Pointer + attr tag for GetAtt
}

// Exported values - these are what users interact with
var MyRole = myRole{
    RoleName: "my-role",
}

var MyFunction = myFunction{
    FunctionName: "processor",
    Role:         &MyRole.Role,
}

func init() {
    wetwire.Register(&MyRole, &MyFunction)
}

// Attrs accessible via promotion:
MyRole.Arn  // ✓ Promoted from embedded iam.Role
```

**Key principles:**
- Wrapper structs **embed** the resource type (like Python's `resource:` annotation)
- Embedding **promotes attrs** (`.Arn`, `.RoleId`) to wrapper level
- Unexported type, exported value enables `MyRole.Arn` syntax
- PascalCase field names match CF property names (no tags needed)
- Tags only for: nested paths, GetAtt (`attr:"Arn"`), or name overrides
- References are **pointers** to embedded resource types

### How It Works

**Generated resource types have attr fields:**

```go
// iam/role.go (generated)
type Role struct {
    // Attrs - populated by Register()
    Arn    AttrRef
    RoleId AttrRef

    // Properties (no tags needed - PascalCase matches CF)
    RoleName                 string
    AssumeRolePolicyDocument *PolicyDocument
}
```

**Wrapper embeds resource, promotes attrs:**

```go
type myRole struct {
    iam.Role  // Embedding promotes Arn, RoleId to wrapper
    RoleName string
}
```

**Registration populates attrs:**

```go
func init() {
    wetwire.Register(&MyRole, &MyFunction)
    // Populates MyRole.Arn.Target = "MyRole", etc.
}
```

**Serialization detects pointers to registered resources:**

```go
// Framework sees Role: &MyRole.Role (pointer to iam.Role)
// Checks for `attr:"Arn"` tag → GetAtt
// Otherwise → Ref
```

### Pattern Translation Table

| Python | Go | Serializes To |
|--------|-----|---------------|
| `MyRole` | `&MyRole` | `{"Ref": "MyRole"}` |
| `MyRole.Arn` | `&MyRole` + `attr:"Arn"` tag | `{"Fn::GetAtt": ["MyRole", "Arn"]}` |
| `[MyStatement]` | `[]*Statement{&MyStatement}` | Array of Refs |
| `MyRole.Arn` (external) | `MyRole.Arn` | Direct field access |

### GetAtt via Struct Tags

```go
var MyFunction = lambda.Function{
    Role:   &MyRole,    // Pointer reference
}

// In generated lambda.Function:
type Function struct {
    Role *iam.Role `cf:"Role" attr:"Arn"`  // Tag tells framework: use GetAtt
}
```

### Why This Works

1. **Flat**: No wrapper types, just struct values
2. **Idiomatic**: Pointers for references, struct tags for metadata
3. **Type-safe**: `&MyRole` only accepts `*iam.Role`
4. **Dot syntax**: `MyRole.Arn` works because Arn is an embedded field
5. **Analyzable**: Framework extracts dependencies from pointer fields

---

## GO-SPECIFIC IMPLEMENTATION NOTES

### 1. No Runtime Decorators
Python uses `@wetwire_aws` decorator. Go uses:
- Struct embedding for resource type indication
- `init()` functions for registration
- Reflection to detect embedded types and pointers

### 2. Embedding = Resource Type
```go
// Python: resource: iam.Role
// Go: Embedded type
type myRole struct {
    iam.Role  // This IS the resource type indicator
    RoleName string
}
```

### 3. Reference Pattern
```go
// Python: role = MyRole
// Go: Pointer to embedded resource
type myFunction struct {
    lambda.Function
    Role *iam.Role  // Pointer = Ref
}

// Python: role = MyRole.Arn
// Go: Pointer + attr tag
type myFunction struct {
    lambda.Function
    Role *iam.Role `attr:"Arn"`  // Pointer + tag = GetAtt
}
```

### 4. Attr Promotion
```go
// Embedded type promotes its fields
type myRole struct {
    iam.Role  // Has Arn, RoleId fields
    RoleName string
}

var MyRole = myRole{...}
MyRole.Arn  // ✓ Promoted from iam.Role
```

### 5. Registration
```go
func init() {
    wetwire.Register(&MyRole, &MyFunction)
    // - Detects embedded resource types
    // - Populates attr fields (Arn.Target = "MyRole")
    // - Builds dependency graph from pointer fields
}
```

### 6. Serialization
```go
// Framework sees Role: &MyRole.Role
// Checks attr tag → GetAtt or Ref
// Emits {"Fn::GetAtt": ["MyRole", "Arn"]} or {"Ref": "MyRole"}
```

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
    "wetwire"
    "wetwire/aws/iam"
    "wetwire/aws/lambda"
    "wetwire/aws/s3"
)

// ============================================================
// Python equivalent:
//   class DataBucket:
//       resource: s3.Bucket
//       bucket_name = "data"
// ============================================================
type dataBucket struct {
    s3.Bucket
    BucketName string
}

var DataBucket = dataBucket{
    BucketName: "data",
}

// ============================================================
// Python equivalent:
//   class ProcessorRole:
//       resource: iam.Role
//       assume_role_policy_document = LambdaAssumeRolePolicy
// ============================================================
type processorRole struct {
    iam.Role
    RoleName                 string
    AssumeRolePolicyDocument *iam.PolicyDocument
}

var ProcessorRole = processorRole{
    RoleName:                 "processor-role",
    AssumeRolePolicyDocument: &LambdaAssumeRolePolicy.PolicyDocument,
}

// ============================================================
// Python equivalent:
//   class ProcessorFunction:
//       resource: lambda_.Function
//       role = ProcessorRole.Arn
//       bucket = DataBucket
// ============================================================
type processorFunction struct {
    lambda.Function
    FunctionName string
    Role         *iam.Role `attr:"Arn"`
    Bucket       *s3.Bucket
}

var ProcessorFunction = processorFunction{
    FunctionName: "processor",
    Role:         &ProcessorRole.Role,
    Bucket:       &DataBucket.Bucket,
}

func init() {
    wetwire.Register(&DataBucket, &ProcessorRole, &ProcessorFunction)
}

// Usage:
// ProcessorRole.Arn  → AttrRef for external use
// &ProcessorRole.Role → pointer for references
```

### Registry Implementation

```go
type Registry struct {
    mu        sync.RWMutex
    resources map[string]any
    deps      map[string][]string
}

func (r *Registry) Register(resources ...any) {
    r.mu.Lock()
    defer r.mu.Unlock()

    for _, res := range resources {
        r.registerOne(res)
    }
}

func (r *Registry) registerOne(resource any) {
    v := reflect.ValueOf(resource).Elem()
    t := v.Type()

    // Find the logical name from variable name (via caller analysis or explicit)
    name := getLogicalName(resource)
    r.resources[name] = resource
    r.deps[name] = []string{}

    // Find embedded resource type and populate its attrs
    for i := 0; i < t.NumField(); i++ {
        field := t.Field(i)
        if field.Anonymous && isResourceType(field.Type) {
            populateAttrs(v.Field(i), name)
        }
    }

    // Extract dependencies from pointer fields
    for i := 0; i < t.NumField(); i++ {
        field := t.Field(i)
        if field.Type.Kind() == reflect.Ptr && isResourceType(field.Type.Elem()) {
            targetName := resolveTargetName(v.Field(i))
            r.deps[name] = append(r.deps[name], targetName)
        }
    }
}
```

### Template Building

```go
template := wetwire.NewTemplate()
template.FromRegistry(registry)

json, err := template.ToJSON()
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
type policyDocument struct {
    iam.PolicyDocument
    Statement []*iam.Statement
}

var MyPolicy = policyDocument{
    Statement: []*iam.Statement{
        &AllowS3Access.Statement,
        &AllowLogsWrite.Statement,
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

**1. No Parens Pattern (Embedded Types + Pointer References)**

The core innovation is referencing resources without instantiation:

```go
// CDK/Pulumi/goformation: INSTANTIATE resources with parens
bucket := s3.NewBucket(stack, "MyBucket", &s3.BucketProps{...})
function := lambda.NewFunction(stack, "MyFunction", &lambda.FunctionProps{
    Environment: map[string]string{"BUCKET": bucket.BucketName()},
})

// wetwire: Embed type, reference by pointer
type myBucket struct {
    s3.Bucket
    BucketName string
}
var MyBucket = myBucket{BucketName: "my-bucket"}

type myFunction struct {
    lambda.Function
    Bucket *s3.Bucket  // Pointer = reference
}
var MyFunction = myFunction{Bucket: &MyBucket.Bucket}

// Attrs via promotion:
MyBucket.Arn  // ✓ No method call, just field access
```

**Why this matters:**
| Imperative (CDK/Pulumi) | Declarative (wetwire) |
|-------------------------|----------------------|
| `bucket.BucketName()` | `MyBucket.Arn` |
| Method call at runtime | Field access |
| `s3.NewBucket(...)` | `var MyBucket = myBucket{...}` |
| Relationship via code flow | Relationship via pointers |
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
