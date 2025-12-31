# Wetwire Implementation Checklist for Go

## Purpose

Complete feature matrix for reimplementing wetwire domain and agent packages in Go.
Organized by dependency order with deduplication opportunities identified.

**Related docs:**
- [Go.md](Go.md) - Go ecosystem mappings, patterns, and architectural decisions
- [GoDecisions.md](GoDecisions.md) - Human decisions required for parallel agent execution
- [AWS.md](AWS.md) - AWS domain feasibility study
- [AGENT.md](AGENT.md) - Agent architecture research

---

## Package Structure Overview

```
Go Implementation Target:

wetwire-aws/                    # Library + CLI (importable)
├── internal/                   # Shared utilities
│   ├── discover/               # AST discovery
│   ├── serialize/              # JSON/YAML output
│   └── template/               # CF template building
├── iam/, s3/, lambda/, ...     # Generated resource types
└── cmd/wetwire-aws/            # CLI with JSON output

wetwire-agent/                  # CLI only (NOT a library)
├── internal/                   # All internal packages
│   ├── orchestrator/           # Developer/Runner coordination
│   ├── personas/               # Beginner, expert, terse, etc.
│   ├── scoring/                # Rubric (0-15 scale)
│   └── results/                # RESULTS.md generation
└── cmd/wetwire-agent/          # CLI tool
```

**Key architectural decisions:**

1. **No separate core library** - Unlike Python's `dataclass-dsl`, Go doesn't need one.
   Python's value is runtime metaprogramming; Go uses build-time AST parsing with stdlib.

2. **Agent is CLI-only** - Not importable as a Go library. It's an end-user tool that
   shells out to domain CLIs via `os/exec`.

3. **Domain coupling via CLI** - Agent calls `wetwire-aws build --output=json` and parses
   structured output. No Go import coupling between packages.

4. **Domain-agnostic agent** - Same agent works with any domain (AWS, GCP, Azure) by
   calling different CLIs. Domain CLIs implement a common JSON output contract.

---

## Go User Pattern Summary

The Go implementation uses direct type declarations - no wrappers, no registration:

```go
// User declares resources directly
var MyRole = iam.Role{
    RoleName: "my-role",
}

var MyFunction = lambda.Function{
    FunctionName: "processor",
    Role:         MyRole.Arn,  // GetAtt (field access)
    Bucket:       MyBucket,    // Ref (direct reference)
}

// CLI discovers and builds: wetwire build ./...
```

| Python | Go | CloudFormation |
|--------|-----|----------------|
| `MyRole` | `MyRole` | `{"Ref": "MyRole"}` |
| `MyRole.Arn` | `MyRole.Arn` | `{"Fn::GetAtt": ["MyRole", "Arn"]}` |
| `@wetwire_aws` decorator | N/A - direct type | N/A |
| `resource: iam.Role` | `iam.Role{...}` | N/A |

**Key differences from Python:**
- No wrapper class needed - `var X = Type{...}` suffices
- No decorator - type is explicit
- No `init()`/`Register()` - CLI discovers via `go/ast`
- No IDE stubs - Go's static types provide full IDE support

See [Go.md](Go.md) for detailed patterns and rationale.

---

## LAYER 1: Internal Utilities (wetwire-aws/internal)

*Shared utilities within wetwire-aws - not a separate package*

### 1.1 Type System

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `Ref[T]` type marker | `_types.py` | Direct reference: `MyBucket` | P0 |
| `Attr[T, name]` marker | `_types.py` | Field access: `MyRole.Arn` | P0 |
| `RefList`, `RefDict` | `_types.py` | `[]T`, `map[K]T` (direct types) | P1 |
| `ContextRef` | `_types.py` | `ContextRef` string wrapper | P2 |
| `RefInfo` extraction | `_types.py:get_refs()` | CLI parses AST for references | P0 |
| `AttrRef` runtime marker | `_attr_ref.py` | `AttrRef` struct field on generated types | P0 |

**Note:** Go uses direct type declaration (`var X = Type{...}`) instead of generic wrappers.
References are direct (`MyBucket`) and attrs are field access (`MyRole.Arn`).

### 1.2 Registry & Discovery

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `ResourceRegistry` | `_registry.py` | Built by CLI at build time | P0 |
| `register()` | `_registry.py` | N/A - CLI discovers resources | P0 |
| `get_all(scope)` | `_registry.py` | Filter by package path | P0 |
| `get_by_type()` | `_registry.py` | Type-keyed lookup | P1 |
| `get_by_name()` | `_registry.py` | Name-keyed lookup | P0 |
| Auto-register | `init()` | CLI discovery via `go/ast` | P0 |

**Note:** No `init()` or `Register()` calls needed. CLI parses source files using
`go/ast` to find `var X = Type{...}` patterns (like Python's `wetwire-aws build`).

### 1.3 Resource Base

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `Resource` interface | `_resource.py` | Interface with ToDict() | P0 |
| `PropertyType` interface | `_property_type.py` | Interface with ToDict() | P0 |
| `resource_type` class var | `_resource.py` | Struct field or method | P0 |

### 1.4 Template

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `Template` struct | `_template.py` | Struct with fields | P0 |
| `from_registry()` | `_template.py` | Constructor function | P0 |
| `add_resource()` | `_template.py` | Method | P0 |
| `get_dependency_order()` | `_template.py` | Topological sort | P0 |
| `to_dict()` | `_template.py` | Method returning map | P0 |
| `to_json()` | `_template.py` | json.Marshal | P0 |
| `to_yaml()` | `_template.py` | yaml.Marshal | P1 |
| `validate()` | `_template.py` | Return []error | P1 |
| `RefTransformer` callback | `_template.py` | Function type | P1 |

### 1.5 Dependency Ordering

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `get_all_dependencies()` | `_ordering.py` | Reflection-based | P0 |
| `topological_sort()` | `_ordering.py` | Kahn's algorithm | P0 |
| `detect_cycles()` | `_ordering.py` | Tarjan's SCC | P1 |
| `get_dependency_graph()` | `_ordering.py` | Map[Type][]Type | P0 |

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

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `LintIssue` struct | `_cli.py` | Struct | P1 |
| `add_common_args()` | `_cli.py` | Persistent flags | P1 |
| Command factories | `_cli.py` | cobra.Command | P1 |
| Config loading | N/A | Multi-source config | P2 |

---

## LAYER 2: AWS Resource Types & CLI (wetwire-aws)

*Main package - includes internal utilities from Layer 1*

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
| `Ref` | `intrinsics/functions.py` | Struct with MarshalJSON | P0 |
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
| `ref()` helper | `intrinsics/refs.py` | N/A - use `MyBucket` directly | P0 |
| `get_att()` helper | `intrinsics/refs.py` | N/A - use `MyRole.Arn` directly | P0 |
| `DeferredRef` | `intrinsics/refs.py` | N/A - CLI resolves at build time | P1 |
| `DeferredGetAtt` | `intrinsics/refs.py` | N/A - CLI resolves at build time | P1 |
| `ARN` constant | `intrinsics/refs.py` | N/A - use `.Arn` field | P0 |
| `Attributes` enum | `intrinsics/refs.py` | Fields on generated types | P0 |

**Note:** Go doesn't need `ref()`/`get_att()` helper functions. Direct references
(`MyBucket`) and field access (`MyRole.Arn`) replace them. CLI detects reference
types during AST parsing.

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

| Command | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `build` | `cli.py` | cobra command + AST discovery | P0 |
| `validate` | `cli.py` | cobra command | P1 |
| `list` | `cli.py` | cobra command | P1 |
| `lint` | `cli.py` | cobra command | P1 |
| `import` | `cli.py` | cobra command | P2 |
| `init` | `cli.py` | cobra command | P1 |

**Note:** `build` command parses Go source using `go/ast` to discover resources
(`var X = Type{...}`), extract dependencies, and generate CloudFormation template.

### 2.12 Code Generation (Build-Time)

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| CF spec fetcher | `codegen/fetch.py` | HTTP client | P0 |
| Spec parser | `codegen/parse.py` | JSON unmarshaling | P0 |
| Enum extractor | `codegen/extract_enums.py` | AWS SDK models | P0 |
| Code generator | `codegen/generate.py` | text/template or jennifer | P0 |
| Schema types | `codegen/schema.py` | Structs | P0 |
| Attr fields | N/A | Generate `Arn`, `RoleId`, etc. as `AttrRef` fields | P0 |

**Generated type example:**
```go
type Role struct {
    // Attrs (for GetAtt)
    Arn    AttrRef
    RoleId AttrRef

    // Properties (user sets these)
    RoleName                 string
    AssumeRolePolicyDocument *PolicyDocument
}
```

---

## LAYER 3: Agent CLI (wetwire-agent)

*CLI-only tool - does NOT import domain packages. Interacts via `os/exec` to domain CLIs.*

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

| Feature | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `ToolResult` | `agents.py` | Struct | P0 |
| `DeveloperAgent` | `agents.py` | Struct | P0 |
| `RunnerAgent` | `agents.py` | Struct | P0 |
| `get_tools()` | `agents.py` | Method returning tool defs | P0 |
| `execute_tool()` | `agents.py` | Method | P0 |
| `run_turn()` | `agents.py` | Method | P0 |
| `run_turn_streaming()` | `agents.py` | SSE streaming | P1 |

**Runner Tools (all use stdlib, no domain imports):**
- `init_package` - Create new package (`os.MkdirAll`, `os.WriteFile`)
- `write_file` - Write file to package (`os.WriteFile`)
- `read_file` - Read file from package (`os.ReadFile`)
- `run_lint` - `exec.Command("wetwire-aws", "lint", "--output=json")`
- `run_build` - `exec.Command("wetwire-aws", "build", "--output=json")`
- `ask_developer` - Ask clarification (Anthropic API)

**Domain CLI contract (JSON output):**
```json
{"success": true, "resources": [...], "errors": [...]}
```

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

| Command | Python Source | Go Pattern | Priority |
|---------|---------------|------------|----------|
| `design` | `cli.py` | cobra command | P0 |
| `test` | `cli.py` | cobra command | P1 |
| `list` | `cli.py` | cobra command | P0 |
| `run-scenario` | `cli.py` | cobra command | P0 |
| `validate-scenarios` | `cli.py` | cobra command | P0 |
| Interactive I/O | N/A | bufio, os.Stdin | P0 |

---

## DEDUPLICATION OPPORTUNITIES

### Shared Utilities (wetwire-aws/internal)

| Feature | Go Location |
|---------|-------------|
| `toSnakeCase()` | `internal/naming` |
| `toPascalCase()` | `internal/naming` |
| `LintIssue` struct | `internal/lint` |
| AST discovery | `internal/discover` |
| Template base | `internal/template` |
| Serialization | `internal/serialize` |

### Contract Between wetwire-aws and wetwire-agent

Agent does NOT import domain packages. They communicate via CLI JSON output.

| Contract | Description |
|----------|-------------|
| `--output=json` flag | All domain CLI commands support JSON output |
| Lint result JSON | `{"issues": [...], "fixable": [...]}` |
| Build result JSON | `{"success": bool, "template": {...}, "errors": [...]}` |
| Exit codes | 0=success, 1=error, 2=lint issues |

---

## IMPLEMENTATION ORDER

### Phase 1: wetwire-aws (can be built independently)
1. Internal utilities (`internal/`)
   - AttrRef type
   - AST discovery (`go/ast` parsing)
   - Serialization helpers
   - Dependency ordering
2. Intrinsic function structs (Ref, GetAtt, Sub, etc.)
3. Base types (CloudFormationResource, Template)
4. Code generator (from CF spec → types with AttrRef fields)
5. CLI (`cmd/wetwire-aws/`)
   - `build --output=json` command with AST discovery
   - `lint --output=json`, `validate`, `import` commands

### Phase 2: wetwire-agent (can be built independently)
*No Go import dependency on wetwire-aws - just needs CLI installed*

1. Personas and scoring (`internal/personas`, `internal/scoring`)
2. Results writer (`internal/results`)
3. Domain runner (shells out to domain CLIs, parses JSON)
4. Orchestrator (`internal/orchestrator`)
5. AI agents (Anthropic Go SDK)
6. CLI (`cmd/wetwire-agent/`)

**Note:** Phases can be developed in parallel since they only share CLI contracts, not Go imports.

---

## STATISTICS

| Package | Public Functions | Public Types | Lines of Code |
|---------|------------------|--------------|---------------|
| dataclass-dsl | ~50 | ~25 | ~2,000 |
| wetwire-aws | ~100 | ~50 | ~5,000 |
| wetwire-agent | ~60 | ~30 | ~3,000 |
| **Total** | **~210** | **~105** | **~10,000** |

*Note: wetwire-aws generated resources add ~50,000 lines but are code-generated*
