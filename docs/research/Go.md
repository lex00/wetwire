# Wetwire Go Implementation

**Status**: Research complete
**Purpose**: Document Go ecosystem mappings, patterns, and architectural decisions for implementing wetwire in Go.
**Scope**: Go-specific design decisions; see `ImplementationChecklist.md` for feature matrix.
**Recommendation**: **Viable** - Pointers to wrapper types (`*MyVPC`) enable the "no parens" pattern idiomatically.

---

## Executive Summary

Implementing wetwire in Go requires translating Python's dynamic "no parens" pattern to Go's static type system. The key insight: **Pointers to wrapper types (`*MyVPC`) naturally express references**, achieving the same declarative wiring as Python with idiomatic Go.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Python (dynamic)                    Go (static)                         │
│                                                                          │
│  vpc_id = ref(MyVPC)          →      VpcID    *MyVPC                    │
│  role: Attr[MyRole, "Arn"]    →      Role     *MyRole `attr:"Arn"`      │
│  statement = [MyStatement]    →      Statement []*MyStatement           │
│                                                                          │
│  Class reference              →      Pointer to wrapper type            │
│  Runtime introspection        →      Reflection on pointer types        │
│  Forward refs via strings     →      Type must exist (file ordering)    │
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

**wetwire (Declarative - NO Parens on References):**
```go
// Wrapper struct declares ALL wiring - NO instantiation of referenced types
type MyBucket struct {
    wetwire.Base
    Resource   s3.Bucket
    BucketName string `cf:"BucketName"`
}

type MyFunction struct {
    wetwire.Base
    Resource lambda.Function
    Bucket   *MyBucket  // ← NO parens! Pointer to type, not instantiation
    //       ↑ This is the "no parens" pattern in Go
    //       *MyBucket means "reference TO MyBucket type"
    //       not "create a MyBucket instance"
}

// init() auto-registers - dependencies extracted from pointer fields
func init() {
    wetwire.Register(&MyBucket{})
    wetwire.Register(&MyFunction{})
    // Registry sees *MyBucket in MyFunction, adds to dependency graph
}

// Template built from registry - topologically sorted
template := cfn.FromRegistry()  // MyBucket comes before MyFunction automatically
```

**The Key Difference:**
```go
// goformation: Ref("MyBucket") - string argument, loses type info
// wetwire:     *MyBucket       - pointer type, compiler-checked

// goformation: lambda.Function{...} - instantiate, then add to map
// wetwire:     Bucket *MyBucket     - declare relationship, no instantiation
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

The "no parens" pattern is wetwire's signature feature: **referencing types without instantiating them**. This is the core of declarative wiring.

### Python User Syntax

```python
class MySubnet:
    resource: ec2.Subnet
    vpc_id = ref(MyVPC)                    # Ref via helper function
    # or just: vpc_id = MyVPC              # Naked class reference

class MyRole:
    resource: iam.Role
    assume_role_policy_document = MyPolicy  # Naked class

class ProcessorFunction:
    resource: lambda_.Function
    role = ProcessorRole.Arn               # GetAtt via attribute access
    bucket = ref(DataBucket)               # Ref via helper
    # or: role = get_att(ProcessorRole, "Arn")
```

All variations result in: **naked class reference, no parentheses**.

### Why "No Parens" Matters

| Benefit | Explanation |
|---------|-------------|
| **Declarative** | Relationships ARE the code, not method calls |
| **Analyzable** | Dependencies extracted statically before runtime |
| **Refactorable** | Rename class → all references update (IDE support) |
| **Type-safe** | Invalid class reference → type error |
| **Concise** | `vpc_id = ref(MyVPC)` vs `vpc_id = ref(MyVPC())` |

### Go Translation: Pointers as References

In Go, **pointers naturally express "reference to"** - exactly what we need:

```go
type MySubnet struct {
    Resource ec2.Subnet
    VpcID    *MyVPC  // Pointer = reference, not embedding
}
```

The framework:
1. Detects `*MyVPC` is a pointer to a registered wrapper type
2. Serializes as `{"Ref": "MyVPC"}` automatically
3. Extracts dependency: MySubnet depends on MyVPC

### Pattern Translation Table

| Python | Go | Serializes To |
|--------|-----|---------------|
| `MyVPC` | `*MyVPC` | `{"Ref": "MyVPC"}` |
| `ref(MyVPC)` | `*MyVPC` | `{"Ref": "MyVPC"}` |
| `MyRole.Arn` | `*MyRole` + `attr:"Arn"` | `{"Fn::GetAtt": ["MyRole", "Arn"]}` |
| `[MyStatement]` | `[]*MyStatement` | Array of Refs |
| `MyPolicy` | `*MyPolicy` | Inline or Ref (context-dependent) |

### GetAtt via Struct Tags

Python `MyRole.Arn` becomes a pointer with an `attr` tag in Go:

```go
type MyFunction struct {
    Resource lambda.Function
    Role     *MyRole   `cf:"Role" attr:"Arn"`  // → {"Fn::GetAtt": ["MyRole", "Arn"]}
    Bucket   *MyBucket `cf:"Environment.Variables.BUCKET"`  // → {"Ref": "MyBucket"}
}
```

The framework checks:
- If `attr` tag present → serialize as GetAtt
- Otherwise → serialize as Ref

### Forward References

Both Python and Go require types to exist - Python just hides it via runtime resolution and `setup_resources()` file ordering. Go handles it the same way:

1. **File ordering**: Define dependencies before dependents
2. **Separate packages**: Put shared types in base package
3. **Framework tooling**: Analyze files, report ordering issues

This is the same constraint - just surfaced at compile time instead of runtime.

### Implementation Priority

| Feature | Priority | Approach |
|---------|----------|----------|
| Pointer detection | P0 | Reflect on `*WrapperType` fields |
| Ref serialization | P0 | MarshalJSON on wrapper types |
| GetAtt via `attr` tag | P0 | Check tag, serialize differently |
| Dependency extraction | P0 | Build graph from pointer fields |
| File ordering | P1 | Framework tooling or documentation |

---

## GO-SPECIFIC IMPLEMENTATION NOTES

### 1. No Runtime Decorators
Python uses `@wetwire_aws` decorator. Go uses:
- Struct embedding (`wetwire.Base`) for shared behavior
- Interface implementation for resource contract
- `init()` functions for auto-registration

### 2. No `__annotations__`
Python introspects type hints at runtime. Go uses:
- `reflect` package to inspect struct fields
- Struct tags for metadata (`cf:`, `attr:`)
- Pointer type detection for references

### 3. Reference Pattern
```go
// Python: vpc_id = ref(MyVPC)
// Go: Pointer to wrapper type
type MySubnet struct {
    Resource ec2.Subnet
    VpcID    *MyVPC `cf:"VpcId"`
}

// Python: role = ProcessorRole.Arn (or get_att(ProcessorRole, "Arn"))
// Go: Pointer with attr tag
type MyFunction struct {
    Resource lambda.Function
    Role     *ProcessorRole `cf:"Role" attr:"Arn"`
}
```

### 4. Registry Pattern
```go
// Auto-registration via init()
func init() {
    wetwire.Register(&MyBucket{})
    // Registration extracts pointer fields, builds dependency graph
}
```

### 5. Serialization
```go
// Framework handles pointer serialization automatically
type MyFunction struct {
    Resource lambda.Function
    Bucket   *MyBucket `cf:"Environment.Variables.BUCKET"`
}

// When serializing, framework sees *MyBucket and emits:
// {"Ref": "MyBucket"}
// If attr:"Arn" tag present, emits:
// {"Fn::GetAtt": ["MyBucket", "Arn"]}
```

### 6. Dependency Analysis
```go
// At registration, extract all pointer-to-wrapper fields
func Register(resource any) {
    t := reflect.TypeOf(resource).Elem()
    for i := 0; i < t.NumField(); i++ {
        field := t.Field(i)
        // Check if field is pointer to registered wrapper type
        if field.Type.Kind() == reflect.Ptr {
            targetType := field.Type.Elem()
            if isWrapperType(targetType) {
                addDependency(t, targetType)
            }
        }
    }
}
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

### No Parens Pattern (Core Innovation)

The following shows how Python's "no parens" pattern translates to Go:

```go
// ============================================================
// Python equivalent:
//   class DataBucket:
//       resource: s3.Bucket
//       bucket_name = "data"
// ============================================================
type DataBucket struct {
    wetwire.Base
    Resource   s3.Bucket
    BucketName string `cf:"BucketName"`
}

// ============================================================
// Python equivalent:
//   class ProcessorRole:
//       resource: iam.Role
//       assume_role_policy_document = LambdaAssumeRolePolicy
// ============================================================
type ProcessorRole struct {
    wetwire.Base
    Resource                 iam.Role
    AssumeRolePolicyDocument *LambdaAssumeRolePolicy `cf:"AssumeRolePolicyDocument"`
}

// ============================================================
// Python equivalent:
//   class ProcessorFunction:
//       resource: lambda_.Function
//       role = ProcessorRole.Arn
//       bucket = DataBucket
// ============================================================
type ProcessorFunction struct {
    wetwire.Base
    Resource lambda.Function
    Role     *ProcessorRole `cf:"Role" attr:"Arn"`
    Bucket   *DataBucket    `cf:"Environment.Variables.BUCKET"`
}

// Registration via init() - extracts pointer fields for dependency graph
func init() {
    wetwire.Register(&DataBucket{})
    wetwire.Register(&ProcessorRole{})
    wetwire.Register(&ProcessorFunction{})
}
```

### Registry with Dependency Extraction

```go
type Registry struct {
    mu        sync.RWMutex
    resources map[string]any
    deps      map[string][]string  // resource -> dependencies
}

// Register extracts pointer-to-wrapper fields for dependency graph
func (r *Registry) Register(resource any) {
    r.mu.Lock()
    defer r.mu.Unlock()

    t := reflect.TypeOf(resource).Elem()
    name := t.Name()
    r.resources[name] = resource
    r.deps[name] = []string{}

    // Extract dependencies from pointer fields
    for i := 0; i < t.NumField(); i++ {
        field := t.Field(i)

        // Check if field is pointer to a wrapper type
        if field.Type.Kind() == reflect.Ptr {
            targetType := field.Type.Elem()
            if isWrapperType(targetType) {
                r.deps[name] = append(r.deps[name], targetType.Name())
            }
        }
    }
}

// TopologicalOrder returns resources in dependency order
func (r *Registry) TopologicalOrder() ([]string, error) {
    // Kahn's algorithm using r.deps
    // ...
}

// isWrapperType checks if type has a Resource field (wrapper pattern)
func isWrapperType(t reflect.Type) bool {
    _, hasResource := t.FieldByName("Resource")
    return hasResource
}
```

### Serialization with Pointer Detection

```go
// serializeField handles pointer-to-wrapper fields
func serializeField(field reflect.StructField, value reflect.Value) any {
    // Check for attr tag (GetAtt vs Ref)
    attrTag := field.Tag.Get("attr")

    if field.Type.Kind() == reflect.Ptr && isWrapperType(field.Type.Elem()) {
        targetName := field.Type.Elem().Name()

        if attrTag != "" {
            // GetAtt: {"Fn::GetAtt": ["ResourceName", "Attribute"]}
            return map[string][]string{
                "Fn::GetAtt": {targetName, attrTag},
            }
        }
        // Ref: {"Ref": "ResourceName"}
        return map[string]string{"Ref": targetName}
    }

    // Regular field - return value
    return value.Interface()
}
```

### Template Building

```go
template := cfn.NewTemplate()
template.FromRegistry(registry, cfn.WithScope("mypackage"))

// Resources are serialized in dependency order
json, err := template.ToJSON()
if err != nil {
    log.Fatal(err)
}

// Output includes properly resolved Ref/GetAtt intrinsics:
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

### Slice of References Pattern

For Python's `statement = [MyStatement]` pattern (class in list):

```go
type PolicyDocument struct {
    wetwire.Base
    Resource  iam.PolicyDocument
    Statement []*AssumeRoleStatement `cf:"Statement"`  // Slice of pointers
}
```

The framework iterates the slice and serializes each pointer as a Ref.

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

**1. No Parens Pattern (Type References, Not Instantiation)**

The core innovation is referencing types without instantiating them:

```go
// CDK/Pulumi/goformation: INSTANTIATE resources with parens
bucket := s3.NewBucket(stack, "MyBucket", &s3.BucketProps{...})     // ← parens
function := lambda.NewFunction(stack, "MyFunction", &lambda.FunctionProps{
    Environment: map[string]string{"BUCKET": bucket.BucketName()},  // ← method call
})

// wetwire: REFERENCE types without parens - relationships ARE the code
type MyFunction struct {
    Resource lambda.Function
    Bucket   *MyBucket  // ← NO parens! Pointer to type, not instantiation
    //       ↑ This says "I reference MyBucket" not "create a MyBucket"
    //       The relationship is declared in the struct, not via method calls
}
```

**Why this matters:**
| Imperative (CDK/Pulumi) | Declarative (wetwire) |
|-------------------------|----------------------|
| `bucket.BucketName()` | `*MyBucket` |
| Method call at runtime | Type checked at compile time |
| Relationship via code flow | Relationship via struct fields |
| Dependencies implicit | Dependencies extractable |
| Refactoring breaks refs | Refactoring updates refs |

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
