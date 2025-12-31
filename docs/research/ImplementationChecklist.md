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

#### Paradigm Comparison

**goformation (Imperative):**
```go
template := cloudformation.NewTemplate()

// Resources created imperatively, added to map
bucket := &s3.Bucket{
    BucketName: cloudformation.String("my-bucket"),
}
template.Resources["MyBucket"] = bucket

// Cross-references are strings - no type safety
function := &lambda.Function{
    Environment: &lambda.Function_Environment{
        Variables: map[string]string{
            "BUCKET": cloudformation.Ref("MyBucket"),  // String, not typed
        },
    },
}
template.Resources["MyFunction"] = function
```

**wetwire (Declarative):**
```go
// Wrapper struct declares ALL wiring
type MyBucket struct {
    wetwire.Base
    Resource   s3.Bucket
    BucketName string `cf:"BucketName"`
}

type MyFunction struct {
    wetwire.Base
    Resource    lambda.Function
    Environment FunctionEnvironment
    Bucket      Ref[MyBucket]  // Type-safe reference
}

// init() auto-registers
func init() {
    wetwire.Register(&MyBucket{})
    wetwire.Register(&MyFunction{})
}

// Template built from registry
template := cfn.FromRegistry()  // Dependencies analyzed automatically
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

### 1.1 Type System

| Feature | Python Source | Go Pattern | Go Library | Priority |
|---------|---------------|------------|------------|----------|
| `Ref[T]` type marker | `_types.py` | Generic interface | Go 1.18+ generics | P0 |
| `Attr[T, name]` marker | `_types.py` | Struct with target + attr | Native struct | P0 |
| `RefList`, `RefDict` | `_types.py` | Generic slice/map types | Go 1.18+ generics | P1 |
| `ContextRef` | `_types.py` | Interface for context lookup | Native interface | P2 |
| `RefInfo` extraction | `_types.py:get_refs()` | Reflection or codegen | `reflect` / jennifer | P0 |
| `AttrRef` runtime marker | `_attr_ref.py` | Struct type | Native struct | P0 |

**Go Consideration:** No runtime type annotations. Use:
- Struct tags for metadata (`reflect.StructTag`)
- Code generation with jennifer for type introspection
- Interfaces for polymorphism

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

### 3. Reference Pattern
```go
// Python: parent = MyVPC (no-parens)
// Go: struct field with tag
type MySubnet struct {
    Resource ec2.Subnet
    VpcID    Ref `wetwire:"ref=MyVPC"`
}
```

### 4. Registry Pattern
```go
// Auto-registration via init()
func init() {
    registry.Register(&MyBucket{})
}
```

### 5. Serialization
```go
// Use json/yaml struct tags
type MyBucket struct {
    Resource   s3.Bucket
    BucketName string `json:"BucketName"`
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

### Wrapper Pattern (wetwire-aws)
```go
// User-defined wrapper struct
type MyBucket struct {
    wetwire.Base
    Resource    s3.Bucket `wetwire:"resource"`
    BucketName  string    `cf:"BucketName"`
    Versioning  *MyVersioning `cf:"VersioningConfiguration" wetwire:"ref"`
}

// Registration via init()
func init() {
    wetwire.Register(&MyBucket{})
}
```

### Reference Pattern
```go
// Generic Ref type
type Ref[T any] struct {
    target *T
}

// Intrinsic output
func (r Ref[T]) MarshalJSON() ([]byte, error) {
    name := wetwire.LogicalName(r.target)
    return json.Marshal(map[string]string{"Ref": name})
}
```

### Template Building
```go
template := cfn.NewTemplate()
template.FromRegistry(registry, cfn.WithScope("mypackage"))
json, err := template.ToJSON()
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

**1. Declarative Wrapper Pattern (vs Imperative)**
```go
// CDK/Pulumi/goformation: Imperative
bucket := s3.NewBucket(stack, "MyBucket", &s3.BucketProps{...})
function := lambda.NewFunction(stack, "MyFunction", &lambda.FunctionProps{
    Environment: map[string]string{"BUCKET": bucket.BucketName()},
})

// wetwire: Declarative - relationships defined in struct
type MyFunction struct {
    Resource lambda.Function
    Bucket   Ref[MyBucket]  // Relationship IS the code
}
```

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
