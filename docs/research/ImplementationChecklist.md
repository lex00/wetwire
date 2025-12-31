# Wetwire Implementation Checklist for Go

## Purpose

Complete feature matrix for reimplementing wetwire domain and agent packages in Go.
Organized by dependency order with deduplication opportunities identified.

---

## Package Structure Overview

```
Go Implementation Target:
├── wetwire-core/          # Shared library (from dataclass-dsl)
├── wetwire-aws/           # AWS domain package
└── wetwire-agent/         # Testing/design orchestration
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

## EXISTING GO IaC LIBRARIES TO STUDY

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
| **Declarative wiring** | ❌ Imperative only | ✅ Wrapper pattern | All relationships declared in struct fields |
| **Cross-resource references** | ❌ String-based | ✅ Type-safe | `ref(MyVPC)` validates at compile time |
| **Dependency graph** | ❌ No analysis | ✅ Automatic | Topological sort from Ref/Attr analysis |
| **Multi-file packages** | ❌ Manual wiring | ✅ setup_resources() | Auto-discovery with dependency ordering |
| **AI-assisted generation** | ❌ None | ✅ wetwire-agent | Lint/build feedback loop |
| **Linting** | ❌ None | ✅ Built-in | Catch anti-patterns before build |
| **Template import** | ✅ Parsing only | ✅ Code generation | Import → wetwire code, not just structs |

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

## LAYER 1: Core Library (wetwire-core)

*Source: dataclass-dsl - must be implemented first*

### 1.1 Type System (No Parens Foundation)

The type system enables the **"no parens" pattern** - referencing types without instantiation.

| Feature | Python Source | Go Pattern | Go Library | Priority |
|---------|---------------|------------|------------|----------|
| `Ref[T]` type marker | `_types.py` | `Ref[*T]` generic struct | Go 1.18+ generics | P0 |
| `Attr[T, name]` marker | `_types.py` | `Attr[*T]` + attribute field | Native struct | P0 |
| `RefList`, `RefDict` | `_types.py` | `[]Ref[*T]`, `map[K]Ref[*T]` | Go 1.18+ generics | P1 |
| `ContextRef` | `_types.py` | `ContextRef` string wrapper | Native struct | P2 |
| `RefInfo` extraction | `_types.py:get_refs()` | Reflect on `Ref[T]` fields | `reflect` | P0 |
| `AttrRef` runtime marker | `_attr_ref.py` | Embed in `Attr[T]` | Native struct | P0 |

**Go Implementation for No Parens:**
```go
// Ref[T] enables: VpcID Ref[*MyVPC] (like Python vpc_id = ref(MyVPC))
type Ref[T any] struct {
    logicalName string  // Populated at registration via reflection
}

func (r Ref[T]) MarshalJSON() ([]byte, error) {
    return json.Marshal(map[string]string{"Ref": r.logicalName})
}

// Attr[T] enables: Role Attr[*MyRole] `attr:"Arn"` (like Python role: Attr[MyRole, "Arn"])
type Attr[T any] struct {
    logicalName string
    attribute   string  // From struct tag or explicit
}

func (a Attr[T]) MarshalJSON() ([]byte, error) {
    return json.Marshal(map[string][]string{"Fn::GetAtt": {a.logicalName, a.attribute}})
}
```

**Go Consideration:** No runtime type annotations. Use:
- Struct tags for metadata (`reflect.StructTag`)
- Generic type parameters for type-safe refs (`Ref[*T]`)
- Code generation for forward reference resolution

### 1.2 Registry

| Feature | Python Source | Go Pattern | Go Library | Priority |
|---------|---------------|------------|------------|----------|
| `ResourceRegistry` | `_registry.py` | Mutex-protected map | `sync.RWMutex` | P0 |
| `register()` | `_registry.py` | Method on registry | Native | P0 |
| `get_all(scope)` | `_registry.py` | Filter by package path | Native | P0 |
| `get_by_type()` | `_registry.py` | Type-keyed lookup | `reflect.Type` key | P1 |
| `get_by_name()` | `_registry.py` | Name-keyed lookup | Native | P0 |
| Auto-register | `init()` | Package init functions | Native | P0 |

### 1.3 Resource Base

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `Resource` interface | `_resource.py` | Interface with ToDict() | P0 |
| `PropertyType` interface | `_property_type.py` | Interface with ToDict() | P0 |
| `resource_type` class var | `_resource.py` | Struct field or method | P0 |

### 1.4 Template

| Feature | Python Source | Go Pattern | Go Library | Priority |
|---------|---------------|------------|------------|----------|
| `Template` struct | `_template.py` | Struct with fields | Native | P0 |
| `from_registry()` | `_template.py` | Constructor function | Native | P0 |
| `add_resource()` | `_template.py` | Method | Native | P0 |
| `get_dependency_order()` | `_template.py` | Topological sort | gonum/graph | P0 |
| `to_dict()` | `_template.py` | Method returning map | Native | P0 |
| `to_json()` | `_template.py` | json.Marshal | encoding/json | P0 |
| `to_yaml()` | `_template.py` | yaml.Marshal | gopkg.in/yaml.v3 | P1 |
| `validate()` | `_template.py` | Return []error | Native | P1 |
| `RefTransformer` callback | `_template.py` | Function type | Native | P1 |

### 1.5 Dependency Ordering

| Feature | Python Source | Go Pattern | Go Library | Priority |
|---------|---------------|------------|------------|----------|
| `get_all_dependencies()` | `_ordering.py` | Reflection-based | reflect | P0 |
| `topological_sort()` | `_ordering.py` | Kahn's algorithm | gonum/graph/topo | P0 |
| `detect_cycles()` | `_ordering.py` | Tarjan's SCC | gonum/graph/topo | P1 |
| `get_dependency_graph()` | `_ordering.py` | Map[Type][]Type | Native | P0 |

### 1.6 Serialization

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `FieldMapper` interface | `_serialization.py` | Interface | P0 |
| `PascalCaseMapper` | `_serialization.py` | Implementation | P0 |
| `SnakeCaseMapper` | `_serialization.py` | Implementation | P1 |
| `ValueSerializer` interface | `_serialization.py` | Interface | P0 |
| Recursive serialization | `_serialization.py` | Method | P0 |

### 1.7 Code Generation Utilities

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `to_snake_case()` | `_codegen.py` | Function | P0 |
| `to_pascal_case()` | `_codegen.py` | Function | P0 |
| `sanitize_name()` | `_codegen.py` | Go keywords check | P0 |
| `escape_string()` | `_codegen.py` | strconv.Quote | P0 |

**Go Keywords to Handle:**
```go
var GO_KEYWORDS = []string{
    "break", "case", "chan", "const", "continue", "default", "defer",
    "else", "fallthrough", "for", "func", "go", "goto", "if", "import",
    "interface", "map", "package", "range", "return", "select", "struct",
    "switch", "type", "var",
}
```

### 1.8 Provider Interface

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `Provider` interface | `_provider.py` | Interface | P0 |
| `serialize_ref()` | `_provider.py` | Method | P0 |
| `serialize_attr()` | `_provider.py` | Method | P0 |
| `serialize_resource()` | `_provider.py` | Method | P0 |
| `serialize_template()` | `_provider.py` | Method | P0 |

### 1.9 IR (Intermediate Representation)

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `IRProperty` | `_ir.py` | Struct | P1 |
| `IRParameter` | `_ir.py` | Struct | P1 |
| `IRResource` | `_ir.py` | Struct | P1 |
| `IROutput` | `_ir.py` | Struct | P1 |
| `IRTemplate` | `_ir.py` | Struct | P1 |

### 1.10 CLI Utilities

| Feature | Python Source | Go Pattern | Go Library | Priority |
|---------|---------------|------------|------------|----------|
| `LintIssue` struct | `_cli.py` | Struct | Native | P1 |
| `add_common_args()` | `_cli.py` | Persistent flags | cobra + pflag | P1 |
| Command factories | `_cli.py` | cobra.Command | spf13/cobra | P1 |
| Config loading | N/A | Multi-source config | spf13/viper | P2 |

---

## LAYER 2: AWS Domain Package (wetwire-aws)

*Depends on: wetwire-core*

### 2.1 Base Classes

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `CloudFormationResource` | `base.py` | Embed Resource interface | P0 |
| `PropertyType` | `base.py` | Embed PropertyType interface | P0 |
| `Tag` struct | `base.py` | Struct | P0 |
| `PolicyStatement` | `base.py` | Struct with ToDict() | P0 |
| `DenyStatement` | `base.py` | Embed PolicyStatement | P0 |
| `PolicyDocument` | `base.py` | Struct | P0 |
| `_to_cf_name()` | `base.py` | toCFName() function | P0 |
| `_serialize_value()` | `base.py` | serializeValue() function | P0 |

### 2.2 Template

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `CloudFormationTemplate` | `template.py` | Struct embedding Template | P0 |
| `Parameter` | `template.py` | Struct | P0 |
| `Output` | `template.py` | Struct | P0 |
| `Mapping` | `template.py` | Struct | P1 |
| `Condition` | `template.py` | Struct | P1 |
| `from_registry()` | `template.py` | Constructor | P0 |
| `to_json()` / `to_yaml()` | `template.py` | Methods | P0 |

### 2.3 Intrinsic Functions

| Function | Python Source | Go Pattern | Priority |
|----------|---------------|------------|----------|
| `Ref` | `intrinsics/functions.py` | Struct with ToDict() | P0 |
| `GetAtt` | `intrinsics/functions.py` | Struct | P0 |
| `Sub` | `intrinsics/functions.py` | Struct | P0 |
| `Join` | `intrinsics/functions.py` | Struct | P0 |
| `Select` | `intrinsics/functions.py` | Struct | P1 |
| `If` | `intrinsics/functions.py` | Struct | P0 |
| `Equals` | `intrinsics/functions.py` | Struct | P0 |
| `And` / `Or` / `Not` | `intrinsics/functions.py` | Structs | P1 |
| `Base64` | `intrinsics/functions.py` | Struct | P1 |
| `GetAZs` | `intrinsics/functions.py` | Struct | P1 |
| `ImportValue` | `intrinsics/functions.py` | Struct | P2 |
| `FindInMap` | `intrinsics/functions.py` | Struct | P1 |
| `Split` | `intrinsics/functions.py` | Struct | P2 |
| `Transform` | `intrinsics/functions.py` | Struct | P2 |
| `Cidr` | `intrinsics/functions.py` | Struct | P2 |
| `Condition` | `intrinsics/functions.py` | Struct | P1 |

### 2.4 Reference Helpers

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `ref()` helper | `intrinsics/refs.py` | Function | P0 |
| `get_att()` helper | `intrinsics/refs.py` | Function | P0 |
| `DeferredRef` | `intrinsics/refs.py` | Struct | P1 |
| `DeferredGetAtt` | `intrinsics/refs.py` | Struct | P1 |
| `ARN` constant | `intrinsics/refs.py` | Const | P0 |
| `Attributes` enum | `intrinsics/refs.py` | Constants | P0 |

### 2.5 Pseudo-Parameters

| Constant | Python Source | Go Pattern | Priority |
|----------|---------------|------------|----------|
| `AWS_ACCOUNT_ID` | `intrinsics/pseudo.py` | Var | P0 |
| `AWS_REGION` | `intrinsics/pseudo.py` | Var | P0 |
| `AWS_STACK_NAME` | `intrinsics/pseudo.py` | Var | P0 |
| `AWS_STACK_ID` | `intrinsics/pseudo.py` | Var | P1 |
| `AWS_PARTITION` | `intrinsics/pseudo.py` | Var | P1 |
| `AWS_URL_SUFFIX` | `intrinsics/pseudo.py` | Var | P2 |
| `AWS_NO_VALUE` | `intrinsics/pseudo.py` | Var | P1 |
| `AWS_NOTIFICATION_ARNS` | `intrinsics/pseudo.py` | Var | P2 |

### 2.6 Parameter Types

| Constant | Python Source | Go Pattern | Priority |
|----------|---------------|------------|----------|
| `STRING` | `params.py` | Const | P0 |
| `NUMBER` | `params.py` | Const | P0 |
| `LIST_NUMBER` | `params.py` | Const | P1 |
| `COMMA_DELIMITED_LIST` | `params.py` | Const | P1 |
| `SSM_PARAMETER_*` | `params.py` | Consts | P2 |
| `AVAILABILITY_ZONE` | `params.py` | Const | P1 |
| `AMI_ID` | `params.py` | Const | P1 |
| `VPC_ID` / `SUBNET_ID` | `params.py` | Consts | P1 |
| `SECURITY_GROUP_ID` | `params.py` | Const | P1 |
| `KEY_PAIR` | `params.py` | Const | P1 |

### 2.7 Condition Operators

| Constant | Python Source | Go Pattern | Priority |
|----------|---------------|------------|----------|
| `STRING_EQUALS` | `constants.py` | Const | P1 |
| `STRING_LIKE` | `constants.py` | Const | P1 |
| `NUMERIC_*` | `constants.py` | Consts | P2 |
| `DATE_*` | `constants.py` | Consts | P2 |
| `ARN_*` | `constants.py` | Consts | P1 |
| `IP_ADDRESS` | `constants.py` | Const | P2 |
| `BOOL` / `NULL` | `constants.py` | Consts | P2 |

### 2.8 Provider

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `CloudFormationProvider` | `provider.py` | Struct impl Provider | P0 |
| `serialize_ref()` | `provider.py` | Method | P0 |
| `serialize_attr()` | `provider.py` | Method | P0 |
| `_build_properties()` | `provider.py` | Method | P0 |
| `_serialize_value()` | `provider.py` | Method | P0 |

### 2.9 Linter

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `LintRule` interface | `linter/rules.py` | Interface | P1 |
| `LintIssue` struct | `linter/rules.py` | Struct | P1 |
| `LintContext` | `linter/rules.py` | Struct | P1 |
| `lint_code()` | `linter/__init__.py` | Function | P1 |
| `lint_file()` | `linter/__init__.py` | Function | P1 |
| `fix_code()` | `linter/__init__.py` | Function | P2 |
| Individual rules | `linter/rules.py` | Rule implementations | P1 |

**Lint Rules to Implement:**
- `StringShouldBeParameterType`
- `RefShouldBePseudoParameter`
- `DictShouldBeIntrinsic`
- `DuplicateResource`
- `FileTooLarge`

### 2.10 Importer

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `parse_template()` | `importer/parser.py` | Function | P2 |
| `generate_code()` | `importer/codegen.py` | Function | P2 |
| `generate_package()` | `importer/codegen.py` | Function | P2 |
| `import_template()` | `importer/__init__.py` | Function | P2 |
| YAML/JSON parsing | `importer/parser.py` | yaml/json packages | P2 |

### 2.11 CLI

| Command | Python Source | Go Pattern | Go Library | Priority |
|---------|---------------|------------|------------|----------|
| `build` | `cli.py` | cobra command | spf13/cobra | P0 |
| `validate` | `cli.py` | cobra command | spf13/cobra | P1 |
| `list` | `cli.py` | cobra command | spf13/cobra | P1 |
| `lint` | `cli.py` | cobra command | go/analysis | P1 |
| `import` | `cli.py` | cobra command | spf13/cobra | P2 |
| `init` | `cli.py` | cobra command | spf13/cobra | P1 |

### 2.12 Code Generation (Build-Time)

| Feature | Python Source | Go Pattern | Go Library | Priority |
|---------|---------------|------------|------------|----------|
| CF spec fetcher | `codegen/fetch.py` | HTTP client | net/http | P0 |
| Spec parser | `codegen/parse.py` | JSON unmarshaling | encoding/json | P0 |
| Enum extractor | `codegen/extract_enums.py` | AWS SDK models | aws-sdk-go-v2 | P0 |
| Code generator | `codegen/generate.py` | Template-based | text/template or jennifer | P0 |
| Schema types | `codegen/schema.py` | Structs | Native | P0 |
| Code formatting | N/A | gofmt output | go/format | P0 |

**Go Consideration:** Code generation produces `.go` files, not runtime decoration.
Use `go generate` directive pattern for build-time generation.

---

## LAYER 3: Agent Package (wetwire-agent)

*Depends on: wetwire-aws*

### 3.1 Core Types

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `Message` struct | `runner.py` | Struct | P0 |
| `LintResult` | `runner.py` | Struct | P0 |
| `BuildResult` | `runner.py` | Struct | P0 |
| `CfnLintResult` | `runner.py` | Struct | P0 |
| `ScoreResult` | `runner.py` | Struct | P0 |
| `ScenarioResult` | `runner.py` | Struct | P0 |

### 3.2 Personas

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `Persona` struct | `core/personas.py` | Struct | P0 |
| `BEGINNER` | `core/personas.py` | Var | P0 |
| `INTERMEDIATE` | `core/personas.py` | Var | P0 |
| `EXPERT` | `core/personas.py` | Var | P0 |
| `TERSE` | `core/personas.py` | Var | P0 |
| `VERBOSE` | `core/personas.py` | Var | P0 |
| `load_persona()` | `core/personas.py` | Function | P0 |

### 3.3 Scoring

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `Rating` enum | `core/scoring.py` | Const iota | P0 |
| `Score` struct | `core/scoring.py` | Struct | P0 |
| `score_completeness()` | `core/scoring.py` | Function | P0 |
| `score_lint_quality()` | `core/scoring.py` | Function | P0 |
| `score_code_quality()` | `core/scoring.py` | Function | P0 |
| `score_output_validity()` | `core/scoring.py` | Function | P0 |
| `score_question_efficiency()` | `core/scoring.py` | Function | P0 |
| `calculate_score()` | `core/scoring.py` | Function | P0 |

### 3.4 Results Writer

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `LintCycle` | `core/results.py` | Struct | P0 |
| `Question` | `core/results.py` | Struct | P0 |
| `SessionResults` | `core/results.py` | Struct | P0 |
| `ResultsWriter` | `core/results.py` | Struct | P0 |
| `format()` | `core/results.py` | Method | P0 |
| `write()` | `core/results.py` | Method | P0 |

### 3.5 Orchestrator

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `DeveloperProtocol` | `core/orchestrator.py` | Interface | P0 |
| `RunnerProtocol` | `core/orchestrator.py` | Interface | P0 |
| `SessionConfig` | `core/orchestrator.py` | Struct | P0 |
| `Session` | `core/orchestrator.py` | Struct | P0 |
| `Orchestrator` | `core/orchestrator.py` | Struct | P0 |
| `create_session()` | `core/orchestrator.py` | Method | P0 |
| `run()` | `core/orchestrator.py` | Method | P0 |

### 3.6 Agents

| Feature | Python Source | Go Pattern | Go Library | Priority |
|---------|---------------|------------|------------|----------|
| `ToolResult` | `agents.py` | Struct | Native | P0 |
| `DeveloperAgent` | `agents.py` | Struct | anthropic-sdk-go | P0 |
| `RunnerAgent` | `agents.py` | Struct | anthropic-sdk-go | P0 |
| `get_tools()` | `agents.py` | Method returning tool defs | Native | P0 |
| `execute_tool()` | `agents.py` | Method | os/exec for CLI tools | P0 |
| `run_turn()` | `agents.py` | Method | anthropic-sdk-go | P0 |
| `run_turn_streaming()` | `agents.py` | SSE streaming | anthropic-sdk-go | P1 |

**Runner Tools:**
- `init_package` - Create new package (os.MkdirAll, os.WriteFile)
- `write_file` - Write file to package (os.WriteFile)
- `read_file` - Read file from package (os.ReadFile)
- `run_lint` - Run linter (os/exec)
- `run_build` - Build template (os/exec)
- `ask_developer` - Ask clarification (Anthropic API)

### 3.7 Conversation Handlers

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `AIConversationHandler` | `agents.py` | Struct | P0 |
| `InteractiveConversationHandler` | `agents.py` | Struct | P0 |
| `run()` method | `agents.py` | Method | P0 |

### 3.8 Scenario Runner

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `ScenarioRunner` | `runner.py` | Struct | P0 |
| `load_prompt()` | `runner.py` | Method | P0 |
| `run_lint()` | `runner.py` | Method | P0 |
| `run_build()` | `runner.py` | Method | P0 |
| `run_cfn_lint()` | `runner.py` | Method | P0 |
| `calculate_score()` | `runner.py` | Method | P0 |
| `generate_results_md()` | `runner.py` | Method | P0 |
| `run()` | `runner.py` | Method | P0 |

### 3.9 Domain Integration

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `Prompt` struct | `domains/aws/__init__.py` | Struct | P0 |
| `PROMPTS` library | `domains/aws/__init__.py` | Map | P0 |
| `AwsRunner` | `domains/aws/__init__.py` | Struct | P0 |
| `AwsDomain` | `domains/aws/__init__.py` | Struct | P0 |
| `list_domains()` | `domains/__init__.py` | Function | P0 |
| `get_domain()` | `domains/__init__.py` | Function | P0 |

### 3.10 CLI

| Command | Python Source | Go Pattern | Go Library | Priority |
|---------|---------------|------------|------------|----------|
| `design` | `cli.py` | cobra command | spf13/cobra | P0 |
| `test` | `cli.py` | cobra command | spf13/cobra | P1 |
| `list` | `cli.py` | cobra command | spf13/cobra | P0 |
| `run-scenario` | `cli.py` | cobra command | spf13/cobra | P0 |
| `validate-scenarios` | `cli.py` | cobra command | spf13/cobra | P0 |
| Interactive I/O | N/A | Streaming output | bufio, os.Stdin | P0 |

---

## DEDUPLICATION OPPORTUNITIES

### Shared Between dataclass-dsl and wetwire-aws

| Feature | Current Location | Target Location |
|---------|------------------|-----------------|
| `to_snake_case()` | Both | wetwire-core |
| `to_pascal_case()` | Both | wetwire-core |
| `LintIssue` struct | Both | wetwire-core |
| Registry pattern | Both | wetwire-core |
| Template base | Both | wetwire-core |

### Shared Between wetwire-aws and wetwire-agent

| Feature | Current Location | Target Location |
|---------|------------------|-----------------|
| `LintResult` type | Both (different) | Unify in wetwire-aws |
| CLI utilities | Both | wetwire-core |
| Scoring dimensions | agent only | Keep in agent |

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

---

## IMPLEMENTATION ORDER

### Phase 1: Core Foundation
1. Type system (Ref, Attr, RefInfo)
2. Registry
3. Resource/PropertyType interfaces
4. Serialization (FieldMapper, ValueSerializer)
5. Dependency ordering

### Phase 2: AWS Domain
1. Intrinsic functions
2. CloudFormationResource base
3. CloudFormationProvider
4. CloudFormationTemplate
5. Code generator (from CF spec)
6. CLI commands

### Phase 3: Agent
1. Personas and scoring
2. Results writer
3. Scenario runner
4. Orchestrator
5. AI agents (Anthropic Go SDK)
6. CLI commands

---

## STATISTICS

| Package | Public Functions | Public Types | Lines of Code |
|---------|------------------|--------------|---------------|
| dataclass-dsl | ~50 | ~25 | ~2,000 |
| wetwire-aws | ~100 | ~50 | ~5,000 |
| wetwire-agent | ~60 | ~30 | ~3,000 |
| **Total** | **~210** | **~105** | **~10,000** |

*Note: wetwire-aws generated resources add ~50,000 lines but are code-generated*

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
