# Wetwire Go Implementation

**Status**: Research complete
**Purpose**: Document Go ecosystem mappings, patterns, and architectural decisions for implementing wetwire in Go.
**Scope**: Go-specific design decisions; see `ImplementationChecklist.md` for feature matrix.
**Recommendation**: **Viable** - Go 1.18+ generics enable the "no parens" pattern via `Ref[*T]`.

---

## Executive Summary

Implementing wetwire in Go requires translating Python's dynamic "no parens" pattern to Go's static type system. The key insight: **Go generics (`Ref[*T]`) provide type-safe references without instantiation**, achieving the same declarative wiring as Python.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Python (dynamic)                    Go (static)                         │
│                                                                          │
│  vpc_id = ref(MyVPC)          →      VpcID Ref[*MyVPC]                  │
│  role: Attr[MyRole, "Arn"]    →      Role  Attr[*MyRole] `attr:"Arn"`   │
│  statement = [MyStatement]    →      Statement []Ref[*MyStatement]      │
│                                                                          │
│  Class passed as value        →      Type parameter in generic          │
│  Runtime introspection        →      Compile-time type checking         │
│  Forward refs via strings     →      Requires type to exist or codegen  │
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

### Type System & Generics

| Concept | Go Library | Notes |
|---------|------------|-------|
| Generics | Go 1.18+ | Native support for `Ref[T]` pattern |
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
    Bucket   Ref[*MyBucket]  // ← NO parens! Type parameter, not instantiation
    //       ↑ This is the "no parens" pattern in Go
    //       Ref[*MyBucket] means "reference TO MyBucket type"
    //       not "create a MyBucket instance"
}

// init() auto-registers - dependencies extracted from Ref[T] fields
func init() {
    wetwire.Register(&MyBucket{})
    wetwire.Register(&MyFunction{})
    // Registry sees Ref[*MyBucket] in MyFunction, adds to dependency graph
}

// Template built from registry - topologically sorted
template := cfn.FromRegistry()  // MyBucket comes before MyFunction automatically
```

**The Key Difference:**
```go
// goformation: Ref("MyBucket") - string argument, loses type info
// wetwire:     Ref[*MyBucket]  - type parameter, compiler-checked

// goformation: lambda.Function{...} - instantiate, then add to map
// wetwire:     Bucket Ref[*MyBucket] - declare relationship, no instantiation
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

The "no parens" pattern is wetwire's signature feature: **referencing types without instantiating them**. This is the core of declarative wiring and the primary challenge for Go translation.

### Python "No Parens" Variations

```python
# ============================================================
# PATTERN 1: ref() with class argument (class not instantiated)
# ============================================================
class MySubnet:
    resource: ec2.Subnet
    vpc_id = ref(MyVPC)  # MyVPC is the CLASS, not MyVPC() instance
                          # ref() extracts __name__ → "MyVPC"

# ============================================================
# PATTERN 2: Class as direct value (no function call at all)
# ============================================================
class PolicyDocument:
    resource: iam.PolicyDocument
    statement = [AssumeRoleStatement]  # Class in list, no parens

class MyRole:
    resource: iam.Role
    assume_role_policy_document = PolicyDocument  # Class as value

# ============================================================
# PATTERN 3: Attribute access on class (GetAtt pattern)
# ============================================================
class ProcessorFunction:
    resource: lambda_.Function
    role = ProcessorRole.Arn  # .Arn on CLASS returns GetAtt intrinsic

# ============================================================
# PATTERN 4: Type annotations with class as parameter
# ============================================================
class ProcessorFunction:
    resource: lambda_.Function
    role: Attr[ProcessorRole, "Arn"] = None   # ProcessorRole is type param
    bucket: Ref[DataBucket] = None             # DataBucket is type param
```

### Why "No Parens" Matters

| Benefit | Explanation |
|---------|-------------|
| **Declarative** | Relationships ARE the code, not method calls |
| **Analyzable** | Dependencies extracted statically before runtime |
| **Refactorable** | Rename class → all references update (IDE support) |
| **Type-safe** | Invalid class reference → type error |
| **Concise** | `vpc_id = ref(MyVPC)` vs `vpc_id = ref(MyVPC())` |

### Go Translation Challenge

**Python**: Types are first-class values. You can pass a class as an argument.
**Go**: Types are NOT values. You cannot pass a type to a function.

```go
// ❌ IMPOSSIBLE in Go - types aren't values
func ref(t type) Ref { ... }
vpc_id := ref(MyVPC)  // Cannot pass type as argument

// ❌ ALSO IMPOSSIBLE - can't use type as field value
type MySubnet struct {
    VpcID MyVPC  // This EMBEDS MyVPC, doesn't reference it
}
```

### Go Translation Options

#### Option A: Generic Type Parameters (Recommended for Type Safety)

```go
// Ref[T] generic type - T is the target type
type Ref[T any] struct {
    resolved bool
    value    map[string]string  // {"Ref": "LogicalName"}
}

// Usage - closest to Python pattern
type MySubnet struct {
    wetwire.Base
    Resource ec2.Subnet
    VpcID    Ref[*MyVPC]  // Generic type parameter
}

// Serialization via MarshalJSON
func (r Ref[T]) MarshalJSON() ([]byte, error) {
    // Use reflect to get T's name, or pre-populate at registration
    return json.Marshal(map[string]string{"Ref": r.logicalName})
}
```

**Pros**: Type-safe, IDE autocomplete, refactoring works
**Cons**: Requires types to exist (no forward refs), verbose `[*T]` syntax

#### Option B: Struct Tags (String-based, Allows Forward Refs)

```go
type MySubnet struct {
    wetwire.Base
    Resource ec2.Subnet
    VpcID    Ref `wetwire:"ref=MyVPC"`  // String-based reference
}

// At registration time, parse tags and resolve
func init() {
    wetwire.Register(&MySubnet{})  // Parses tags, validates refs exist
}
```

**Pros**: Forward references work, simple syntax
**Cons**: No type safety, string typos not caught at compile time

#### Option C: Hybrid (Tags + Generics)

```go
type MySubnet struct {
    wetwire.Base
    Resource ec2.Subnet
    // Generic for type safety, tag for metadata
    VpcID    Ref[*MyVPC] `cf:"VpcId"`
}
```

**Pros**: Best of both - type safety AND metadata
**Cons**: More complex, still requires type to exist

#### Option D: Code Generation (Most Go-Idiomatic)

Generate a `_wiring.go` file from analysis:

```go
// mypackage/_wiring.go (GENERATED)
package mypackage

import "wetwire"

func init() {
    wetwire.RegisterWiring(map[string][]wetwire.WireDef{
        "MySubnet": {
            {Field: "VpcID", Target: "MyVPC", Type: wetwire.RefType},
        },
        "MyFunction": {
            {Field: "Role", Target: "MyRole", Attr: "Arn", Type: wetwire.AttrType},
        },
    })
}
```

**Pros**: Forward refs work, fast (no reflection), Go-idiomatic
**Cons**: Requires build step, generated file in repo

### Recommended Approach: Option A + D (Generics + Codegen)

```go
// User writes (checked by compiler):
type MySubnet struct {
    wetwire.Base
    Resource ec2.Subnet
    VpcID    Ref[*MyVPC] `cf:"VpcId"`
}

// `go generate` produces _wiring.go with:
// - Pre-computed logical names
// - Dependency graph
// - Validation that all Ref[T] targets are registered
```

### Pattern Translation Table

| Python Pattern | Go Translation | Notes |
|----------------|----------------|-------|
| `ref(MyVPC)` | `Ref[*MyVPC]{}` or tag | Generic type or struct tag |
| `get_att(MyRole, "Arn")` | `Attr[*MyRole, "Arn"]{}` | Two type params (needs workaround) |
| `ProcessorRole.Arn` | `GetAtt[*ProcessorRole]("Arn")` | Function returning Attr |
| `statement = [MyStatement]` | `Statement []Ref[*MyStatement]` | Slice of generic refs |
| `policy = MyPolicy` | `Policy Ref[*MyPolicy]` | Direct ref as field |
| `bucket: Ref[DataBucket] = None` | `Bucket Ref[*DataBucket]` | Zero value is "unset" |

### GetAtt Challenge

Python `Attr[T, "name"]` has two parameters. Go generics don't support string type parameters:

```go
// ❌ IMPOSSIBLE - Go doesn't have string type parameters
type Attr[T any, Name string] struct {}

// ✅ WORKAROUND 1: Attribute as struct field
type Attr[T any] struct {
    Attribute string
}
role := Attr[*MyRole]{Attribute: "Arn"}

// ✅ WORKAROUND 2: Typed attribute constants
type ArnAttr[T any] struct{}  // Pre-defined for common attrs
role := ArnAttr[*MyRole]{}

// ✅ WORKAROUND 3: Method-based
type MyRole struct { ... }
func (r *MyRole) Arn() Attr { return Attr{LogicalName: "MyRole", Attribute: "Arn"} }
// Usage: role := (&MyRole{}).Arn()  // But this instantiates!

// ✅ WORKAROUND 4: Package-level functions
func MyRoleArn() Attr { return Attr{LogicalName: "MyRole", Attribute: "Arn"} }
```

### Forward Reference Problem

Python resolves references at runtime, allowing:
```python
class MyFunction:
    bucket: Ref[MyBucket] = None  # MyBucket defined BELOW

class MyBucket:
    resource: s3.Bucket
```

Go requires types to exist at compile time:
```go
type MyFunction struct {
    Bucket Ref[*MyBucket]  // ❌ ERROR: MyBucket undefined
}

type MyBucket struct {
    Resource s3.Bucket
}
```

**Solutions:**
1. **Reorder files**: Define dependencies first
2. **Separate packages**: Put shared types in base package
3. **String-based refs**: Use tags with string names
4. **Two-pass codegen**: First pass defines types, second adds refs

### Implementation Priority

| Feature | Priority | Approach |
|---------|----------|----------|
| `Ref[T]` type | P0 | Generic struct with MarshalJSON |
| `Attr[T]` with attribute | P0 | Generic struct + attribute field |
| Dependency extraction | P0 | Reflect on Ref[T] fields at registration |
| Forward references | P1 | String tags or two-pass codegen |
| Class-as-value pattern | P1 | Use `Ref[T]` consistently |
| `.Arn` accessor pattern | P2 | Code generation for common attrs |

---

## GO-SPECIFIC IMPLEMENTATION NOTES

### 1. No Runtime Decorators
Python uses `@wetwire_aws` decorator. Go uses:
- Code generation for resource types
- Struct embedding for composition
- Interface implementation for behavior

### 2. No `__annotations__`
Python introspects type hints at runtime. Go uses:
- Struct tags for metadata
- Reflection (sparingly)
- Code generation for type info

### 3. Reference Pattern (No Parens Translation)
```go
// Python: vpc_id = ref(MyVPC)
// Go: Generic Ref type with type parameter
type MySubnet struct {
    Resource ec2.Subnet
    VpcID    Ref[*MyVPC] `cf:"VpcId"`
}

// Python: role = ProcessorRole.Arn
// Go: Attr with explicit attribute
type MyFunction struct {
    Resource lambda.Function
    Role     Attr[*ProcessorRole] `cf:"Role" attr:"Arn"`
}
```

### 4. Registry Pattern
```go
// Auto-registration via init()
func init() {
    wetwire.Register(&MyBucket{})
    // Registration extracts Ref[T] fields, builds dependency graph
}
```

### 5. Serialization
```go
// Use json/yaml struct tags + custom MarshalJSON for refs
type MyBucket struct {
    Resource   s3.Bucket
    BucketName string `cf:"BucketName"`
}

// Ref serializes to {"Ref": "LogicalName"}
func (r Ref[T]) MarshalJSON() ([]byte, error) {
    return json.Marshal(map[string]string{"Ref": r.logicalName})
}
```

### 6. Dependency Analysis
```go
// At registration, extract all Ref[T] and Attr[T] fields
func Register(resource any) {
    t := reflect.TypeOf(resource).Elem()
    for i := 0; i < t.NumField(); i++ {
        field := t.Field(i)
        // Check if field type is Ref[T] or Attr[T]
        if isRefType(field.Type) {
            // Extract T from Ref[T], add to dependency graph
            targetType := field.Type.TypeArgs()[0]
            addDependency(t, targetType)
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
    AssumeRolePolicyDocument Ref[*LambdaAssumeRolePolicy] `cf:"AssumeRolePolicyDocument"`
}

// ============================================================
// Python equivalent:
//   class ProcessorFunction:
//       resource: lambda_.Function
//       role: Attr[ProcessorRole, "Arn"] = None
//       bucket: Ref[DataBucket] = None
// ============================================================
type ProcessorFunction struct {
    wetwire.Base
    Resource lambda.Function
    Role     Attr[*ProcessorRole] `cf:"Role" attr:"Arn"`
    Bucket   Ref[*DataBucket]     `cf:"Environment.Variables.BUCKET"`
}

// Registration via init() - extracts Ref[T]/Attr[T] for dependency graph
func init() {
    wetwire.Register(&DataBucket{})
    wetwire.Register(&ProcessorRole{})
    wetwire.Register(&ProcessorFunction{})
}
```

### Ref[T] and Attr[T] Implementation

```go
// Ref[T] - type-safe reference to another resource
type Ref[T any] struct {
    logicalName string  // Populated by Register() via reflection
}

// Zero value check (like Python's None)
func (r Ref[T]) IsSet() bool {
    return r.logicalName != ""
}

// MarshalJSON produces {"Ref": "LogicalName"}
func (r Ref[T]) MarshalJSON() ([]byte, error) {
    if r.logicalName == "" {
        // Extract from type parameter at marshal time if not set
        var t T
        r.logicalName = reflect.TypeOf(t).Elem().Name()
    }
    return json.Marshal(map[string]string{"Ref": r.logicalName})
}

// Attr[T] - type-safe GetAtt reference
type Attr[T any] struct {
    logicalName string
    attribute   string  // From `attr:"..."` tag
}

// MarshalJSON produces {"Fn::GetAtt": ["LogicalName", "Attribute"]}
func (a Attr[T]) MarshalJSON() ([]byte, error) {
    return json.Marshal(map[string][]string{
        "Fn::GetAtt": {a.logicalName, a.attribute},
    })
}
```

### Registry with Dependency Extraction

```go
type Registry struct {
    mu        sync.RWMutex
    resources map[string]any
    deps      map[string][]string  // resource -> dependencies
}

// Register extracts Ref[T] and Attr[T] fields for dependency graph
func (r *Registry) Register(resource any) {
    r.mu.Lock()
    defer r.mu.Unlock()

    t := reflect.TypeOf(resource).Elem()
    name := t.Name()
    r.resources[name] = resource
    r.deps[name] = []string{}

    // Extract dependencies from Ref[T] and Attr[T] fields
    for i := 0; i < t.NumField(); i++ {
        field := t.Field(i)
        fieldType := field.Type

        // Check if field is Ref[T] or Attr[T]
        if fieldType.Name() == "Ref" || fieldType.Name() == "Attr" {
            // Extract T from the generic type
            if fieldType.NumTypeArg() > 0 {
                targetType := fieldType.TypeArg(0).Elem()  // *T -> T
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

### Alternative: Class-as-Value Pattern

For Python's `statement = [MyStatement]` pattern (class in list):

```go
// Option 1: Slice of Ref (explicit)
type PolicyDocument struct {
    wetwire.Base
    Resource  iam.PolicyDocument
    Statement []Ref[*AssumeRoleStatement] `cf:"Statement"`
}

// Option 2: Interface + type assertion (more flexible)
type PolicyDocument struct {
    wetwire.Base
    Resource  iam.PolicyDocument
    Statement []wetwire.Resource `cf:"Statement"`  // Accepts any registered resource
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
    Bucket   Ref[*MyBucket]  // ← NO parens! Type parameter only
    //       ↑ This says "I reference MyBucket" not "create a MyBucket"
    //       The relationship is declared in the type, not via method calls
}
```

**Why this matters:**
| Imperative (CDK/Pulumi) | Declarative (wetwire) |
|-------------------------|----------------------|
| `bucket.BucketName()` | `Ref[*MyBucket]` |
| Method call at runtime | Type checked at compile time |
| Relationship via code flow | Relationship via type system |
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
