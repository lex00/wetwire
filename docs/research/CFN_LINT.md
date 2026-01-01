# cfn-lint Go Port Feasibility Research

## Overview

[cfn-lint](https://github.com/aws-cloudformation/cfn-lint) is AWS's official CloudFormation linting tool with **265 rules** across **18 categories**.

## Architecture Summary

```
cfn-lint/
├── decode/          # YAML/JSON parsing with line tracking
├── jsonschema/      # Custom JSON Schema validation (12 modules)
├── rules/           # 265 rules in 18 categories
├── template/        # Template parsing + transforms (SAM)
├── schema/          # CloudFormation resource provider schemas
├── formatters/      # Output: text, JSON, SARIF, JUnit
└── runner/          # Execution engine
```

## Difficulty Assessment: HIGH

### What Ports Easily to Go

| Component | Difficulty | Notes |
|-----------|------------|-------|
| YAML/JSON parsing | Easy | Go has good YAML libs |
| Basic rule structure | Easy | Interface-based rules |
| Output formatters | Easy | Text, JSON, SARIF |
| CLI structure | Easy | cobra/spf13 |
| Schema loading | Medium | JSON file parsing |

### What Does NOT Port Directly

| Component | Difficulty | Why |
|-----------|------------|-----|
| **SAM Transforms** | **BLOCKER** | Requires `aws-sam-translator` (Python-only, 4M weekly downloads, complex) |
| **Line number tracking** | Hard | Python YAML libs preserve line info; Go's `gopkg.in/yaml.v3` supports this but differently |
| **Dynamic rule loading** | Hard | `--append-rules` uses Python import system |
| **Custom JSON Schema** | Hard | 12 modules of custom CF-specific JSON Schema validators |
| **265 rules** | Massive effort | Each rule needs manual porting and testing |
| **Graph visualization** | Medium | networkx/pydot/pygraphviz dependencies |

## Major Blockers

### 1. SAM Transform Support (CRITICAL)

cfn-lint uses `aws-sam-translator` to expand SAM templates before linting:
- `AWS::Serverless::Function` → `AWS::Lambda::Function` + `AWS::IAM::Role`
- No Go equivalent exists
- The translator is ~15k lines of Python with complex logic

**Options:**
- Skip SAM support entirely (major feature gap)
- Shell out to Python `sam-translate` CLI
- Port aws-sam-translator to Go (huge undertaking)

### 2. JSON Schema Validation System

cfn-lint v1 rewrote 100+ rules to use JSON Schema validation against [CloudFormation Registry Schemas](https://docs.aws.amazon.com/cloudformation-cli/latest/userguide/resource-type-schema.html).

Custom extensions in `cfnlint/jsonschema/`:
- `_keywords_cfn.py` - CF-specific keywords
- `_resolvers_cfn.py` - CF intrinsic function resolution
- `_format.py` - Custom format validators

Go JSON Schema libs (e.g., `santhosh-tekuri/jsonschema`) would need significant extension.

### 3. Rule Porting Scale

265 rules organized as:

| Range | Category | Example Rules |
|-------|----------|---------------|
| E/W/I 0XXX | Template errors | Parse errors, section validation |
| E/W/I 1XXX | Functions | Ref, GetAtt, Sub, etc. |
| E/W/I 2XXX | Parameters | Type, constraints |
| E/W/I 3XXX | Resources | Property validation |
| E/W/I 4XXX | Metadata | CFN metadata |
| E/W/I 6XXX | Outputs | Export validation |
| E/W/I 7XXX | Mappings | FindInMap |
| E/W/I 8XXX | Conditions | Condition functions |

Each rule is a Python class with:
- Metadata (id, description, tags)
- `match()` method returning `RuleMatch` objects
- Test fixtures (good/bad templates)

## Effort Estimate

| Phase | Effort | Deliverable |
|-------|--------|-------------|
| Core framework | 2-3 weeks | Parser, rule engine, formatters |
| Schema system | 3-4 weeks | JSON Schema with CF extensions |
| Basic rules (E0xxx) | 2 weeks | ~30 template validation rules |
| Function rules (E1xxx) | 2 weeks | Intrinsic function validation |
| Resource rules (E3xxx) | 4-6 weeks | ~100 resource validation rules |
| All remaining rules | 4-6 weeks | Parameters, outputs, conditions |
| SAM support | ??? | Either skip, shell out, or massive port |
| **Total (without SAM)** | **15-20 weeks** | Partial parity |
| **Total (with SAM)** | **25-35 weeks** | Full parity |

## Alternative Approaches

### 1. Minimal Port (Recommended for wetwire)
Port only the rules relevant to wetwire-aws output:
- E0000-E0999: Template structure
- E1xxx: Intrinsic functions (Ref, GetAtt, Sub)
- E3xxx: Basic resource validation
- Skip: SAM, graph, dynamic rules

**Effort:** 6-8 weeks for ~50 essential rules

### 2. Wrapper Approach
Keep cfn-lint as Python, shell out from Go:
```go
cmd := exec.Command("cfn-lint", "--format", "json", templatePath)
```
**Effort:** 1 day
**Downside:** Requires Python runtime

### 3. Full Port
Port everything including SAM translator.
**Effort:** 6-9 months
**Not recommended**

## Go Ecosystem Gaps

| Python Library | Go Equivalent | Status |
|---------------|---------------|--------|
| PyYAML (with line info) | gopkg.in/yaml.v3 | Partial (node API) |
| jsonschema | santhosh-tekuri/jsonschema | Needs CF extensions |
| boto3/botocore | aws-sdk-go-v2 | Available |
| aws-sam-translator | None | **MISSING** |
| networkx (graphs) | gonum/graph | Available |

## Feature Priority for Go Users

Given users can fall back to Python cfn-lint, prioritize features that:
1. Integrate tightly with Go toolchain
2. Are used in CI/CD where Python may not be available
3. Provide value-add beyond what Python offers

### HIGH VALUE (Worth Porting)

| Feature | Why High Value |
|---------|----------------|
| **DOT graph generation** | Visual dependency graphs for docs/debugging - integrates with Go workflows |
| **Template validation (E0xxx)** | Basic structure checks - fast, no schema needed |
| **Ref/GetAtt validation (E1xxx)** | Catch broken references - common errors |
| **JSON output** | Machine-readable for Go tooling integration |
| **SARIF output** | GitHub/IDE integration for code review |
| **Embedded in Go binary** | No Python runtime needed in CI |

### MEDIUM VALUE (Consider)

| Feature | Trade-off |
|---------|-----------|
| **Resource property validation** | Useful but requires maintaining schema sync |
| **Parameter validation** | Helpful but less critical than references |
| **Region-specific checks** | Nice-to-have for multi-region |

### LOW VALUE (Skip - Use Python)

| Feature | Why Low Value |
|---------|---------------|
| **SAM transform** | Complex, Python-only dependency, users can `sam build` first |
| **Dynamic rule loading** | Power-user feature, fall back to Python |
| **Full 265 rules** | Diminishing returns after core rules |
| **Language extensions** | Rare usage, Python fallback fine |
| **Experimental rules** | By definition, unstable |

### DOT Graph Generation (Detailed)

cfn-lint's graph feature generates DOT format showing resource dependencies:
```
digraph G {
  "MyBucket" -> "MyBucketPolicy"
  "MyRole" -> "MyLambda"
}
```

**Go implementation:**
- Parse template, extract Ref/GetAtt/DependsOn
- Build adjacency list
- Output DOT format (trivial text generation)
- Optional: Use `gonum/graph` for analysis

**Effort:** 1-2 days (standalone feature)

## Final Scope (Based on User Input)

**Goal:** Standalone CLI + embeddable library
**SAM:** Skip entirely (users can preprocess with `sam build`)
**Rules:** All 265 rules (full parity minus SAM)

## Implementation Plan

### Phase 1: Core Framework (3-4 weeks)

```
go/cfn-lint/
├── cmd/cfn-lint/           # CLI
│   └── main.go
├── pkg/                    # Public API (embeddable)
│   ├── lint/               # Main linting interface
│   ├── template/           # Template parsing
│   ├── graph/              # DOT generation
│   └── rules/              # Rule interface
├── internal/
│   ├── decode/             # YAML/JSON with line tracking
│   ├── schema/             # CF resource schemas
│   ├── jsonschema/         # JSON Schema validation
│   ├── formatters/         # Output: text, JSON, SARIF, JUnit
│   └── rules/              # All 265 rule implementations
│       ├── errors/         # E0xxx
│       ├── functions/      # E1xxx
│       ├── parameters/     # E2xxx
│       ├── resources/      # E3xxx
│       ├── metadata/       # E4xxx
│       ├── outputs/        # E6xxx
│       ├── mappings/       # E7xxx
│       └── conditions/     # E8xxx
└── schemas/                # Embedded CF resource schemas
```

**Deliverables:**
- YAML/JSON parser with line number tracking
- Template struct with resource/parameter/output access
- DOT graph generation (resource dependencies)
- Rule interface and registry
- Match/RuleMatch result types
- CLI with `--format json|text|sarif|junit`

### Phase 2: JSON Schema System (3-4 weeks)

Port cfn-lint's custom JSON Schema validation:
- Base JSON Schema validator (use `santhosh-tekuri/jsonschema` as base)
- CF-specific keywords (`_keywords_cfn.py` equivalent)
- CF intrinsic function resolution (`_resolvers_cfn.py`)
- Custom format validators
- Embed CloudFormation resource provider schemas

### Phase 3: Rules - Template & Functions (3-4 weeks)

**E0xxx - Template Errors (~30 rules)**
- Parse errors, duplicate keys
- Required sections (Resources)
- Section validation (Outputs, Parameters, etc.)

**E1xxx - Functions (~25 rules)**
- Ref validation (resource/parameter exists)
- GetAtt validation (resource + attribute exists)
- Sub, Join, Select, If, etc.
- Condition function validation

### Phase 4: Rules - Resources (4-6 weeks)

**E3xxx - Resources (~100 rules)**
- Property type validation
- Required properties
- Allowed values (enums)
- Property dependencies
- UpdatePolicy, DeletionPolicy
- Resource-specific rules

### Phase 5: Rules - Remaining (3-4 weeks)

**E2xxx - Parameters (~20 rules)**
- Type validation
- Constraint validation (AllowedValues, Min/Max)
- Default value validation

**E4xxx - Metadata (~10 rules)**
- cfn-lint directives
- AWS::CloudFormation::Interface

**E6xxx - Outputs (~15 rules)**
- Export validation
- Value validation

**E7xxx - Mappings (~10 rules)**
- FindInMap validation
- Structure validation

**E8xxx - Conditions (~15 rules)**
- Condition function validation
- Circular condition detection

### Phase 6: Polish (2-3 weeks)

- Performance optimization
- Comprehensive test suite
- Documentation
- CI/CD setup
- Example integrations

## Timeline Summary

| Phase | Duration | Rules |
|-------|----------|-------|
| Core Framework | 3-4 weeks | - |
| JSON Schema | 3-4 weeks | - |
| Template + Functions | 3-4 weeks | ~55 |
| Resources | 4-6 weeks | ~100 |
| Remaining | 3-4 weeks | ~60 |
| Polish | 2-3 weeks | ~50 |
| **Total** | **18-25 weeks** | **265** |

## Key Technical Decisions

1. **Line number tracking**: Use `gopkg.in/yaml.v3` Node API
2. **JSON Schema**: Extend `santhosh-tekuri/jsonschema` with CF keywords
3. **Schema embedding**: Use `//go:embed` for resource schemas
4. **Rule registration**: Interface-based with init() registration
5. **Output formats**: Implement text, JSON, SARIF, JUnit, DOT

## Risk Factors

| Risk | Mitigation |
|------|------------|
| JSON Schema complexity | Start with simpler rules, add schema validation incrementally |
| Rule count (265) | Prioritize by usage frequency, port in batches |
| Schema drift | Automate schema updates from AWS |
| Test coverage | Port cfn-lint test fixtures alongside rules |

## NOT in Scope

- SAM transform support
- Dynamic rule loading (`--append-rules`)
- Language extensions transform
- Python interop

## Parallelization Strategy for Claude

The rule porting is highly parallelizable. Here's how to speed up implementation:

### 1. Parallel Rule Porting by Category

Each rule category is independent. Run parallel agents:

```
Agent 1: E0xxx (Template errors)     - 30 rules
Agent 2: E1xxx (Functions)           - 25 rules
Agent 3: E2xxx (Parameters)          - 20 rules
Agent 4: E3xxx (Resources) batch 1   - 50 rules
Agent 5: E3xxx (Resources) batch 2   - 50 rules
Agent 6: E4xxx + E6xxx + E7xxx       - 35 rules
Agent 7: E8xxx (Conditions)          - 15 rules
```

### 2. Rule Porting Template

Each agent follows this pattern per rule:

```go
// 1. Fetch Python source
// https://github.com/aws-cloudformation/cfn-lint/blob/main/src/cfnlint/rules/{category}/{rule}.py

// 2. Create Go file: internal/rules/{category}/{rule_id}.go
package {category}

import "github.com/wetwire/cfn-lint/pkg/rules"

func init() {
    rules.Register(&E{XXXX}{})
}

type E{XXXX} struct{}

func (r *E{XXXX}) ID() string          { return "E{XXXX}" }
func (r *E{XXXX}) ShortDesc() string   { return "..." }
func (r *E{XXXX}) Description() string { return "..." }
func (r *E{XXXX}) Source() string      { return "..." }
func (r *E{XXXX}) Tags() []string      { return []string{...} }

func (r *E{XXXX}) Match(template *template.Template) []rules.Match {
    // Port logic from Python match() method
}

// 3. Port test fixtures
// From: test/fixtures/templates/good/{rule}/
// From: test/fixtures/templates/bad/{rule}/
// To:   internal/rules/{category}/testdata/{rule_id}/

// 4. Create test: internal/rules/{category}/{rule_id}_test.go
```

### 3. Batch Instructions for Agents

**Prompt template for rule porting agents:**

```
Port cfn-lint rules E{START} through E{END} from Python to Go.

For each rule:
1. Read the Python source at:
   https://raw.githubusercontent.com/aws-cloudformation/cfn-lint/main/src/cfnlint/rules/{path}

2. Create Go implementation at:
   internal/rules/{category}/{rule_id}.go

3. Port test fixtures from:
   https://github.com/aws-cloudformation/cfn-lint/tree/main/test/fixtures/templates/good/{rule}
   https://github.com/aws-cloudformation/cfn-lint/tree/main/test/fixtures/templates/bad/{rule}

4. Create test file at:
   internal/rules/{category}/{rule_id}_test.go

Use the existing rule interface and match patterns already established.
Ensure each rule compiles and tests pass before moving to the next.
```

### 4. Dependency Order

Some work must be sequential:

```
Phase 1 (Sequential - Foundation):
├── Template parser with line tracking
├── Rule interface and registry
├── Match/RuleMatch types
└── Basic CLI structure

Phase 2 (Parallel - Can start after Phase 1):
├── Agent 1: E0xxx rules
├── Agent 2: E1xxx rules
├── Agent 3: Output formatters (text, JSON, SARIF)
└── Agent 4: DOT graph generation

Phase 3 (Parallel - Can start after Phase 1):
├── Agent 5: JSON Schema system
├── Agent 6: E2xxx rules
├── Agent 7: E3xxx rules (batch 1)
└── Agent 8: E3xxx rules (batch 2)

Phase 4 (Parallel - After JSON Schema):
├── Agent 9: E4xxx + E6xxx rules
├── Agent 10: E7xxx + E8xxx rules
└── Agent 11: Schema-based resource validation
```

### 5. Speed Optimizations

| Technique | Speedup | Notes |
|-----------|---------|-------|
| **7 parallel agents** | 5-7x | Each handles independent rule batch |
| **Port tests alongside rules** | 1.5x | Don't defer testing |
| **Use existing Go patterns** | 2x | Copy from early rules, adapt |
| **Skip low-value rules initially** | 1.3x | Focus on E/W, skip I (informational) |
| **Batch similar rules** | 1.5x | Port all GetAtt rules together |

### 6. Checkpoints

After each phase, verify:

```bash
# All rules compile
go build ./...

# All tests pass
go test ./internal/rules/... -v

# No regressions
go test ./... -v

# Lint output matches Python for sample templates
./cfn-lint testdata/sample.yaml --format json | diff - expected.json
```

### 7. Attack High-Priority Rules in Parallel

Don't wait to finish all of one category before starting another. Attack the most important rules across categories simultaneously:

**Parallel Sprint 1 - Core Validation (Week 3-4):**
```
Agent A: E0000 (Parse error) + E0001 (Template format)
Agent B: E1001 (Ref undefined) + E1010 (GetAtt undefined)
Agent C: E3001 (Invalid property) + E3002 (Required property)
Agent D: E3012 (Type mismatch) + E3003 (Property type)
```

**Parallel Sprint 2 - Extended Validation (Week 5-6):**
```
Agent A: E1012-E1019 (GetAtt attribute validation)
Agent B: E1020-E1029 (Sub, Join, Select functions)
Agent C: E3004-E3020 (Resource property rules)
Agent D: E2001-E2010 (Parameter validation)
```

**Parallel Sprint 3 - Complete Coverage (Week 7-8):**
```
Agent A: Remaining E0xxx + E1xxx
Agent B: Remaining E2xxx + E3xxx batch 1
Agent C: Remaining E3xxx batch 2
Agent D: E4xxx + E6xxx + E7xxx + E8xxx
```

**Key principle:** Each agent works on the *most valuable* rules available, not sequential rule numbers.

### 8. Rule Priority by Usage

Port high-usage rules first (based on GitHub issues/mentions):

**Tier 1 - Critical (port in Sprint 1):**
| Rule | Description | Why Critical |
|------|-------------|--------------|
| E0000 | Template parse error | Blocks all other linting |
| E1001 | Ref to undefined resource | Most common error |
| E1010 | GetAtt to undefined resource | Second most common |
| E3001 | Invalid resource property | Catches typos |
| E3002 | Required property missing | Catches incomplete resources |
| E3012 | Property value type mismatch | Catches wrong types |

**Tier 2 - High Value (port in Sprint 2):**
| Rule | Description |
|------|-------------|
| E1012 | GetAtt invalid attribute |
| E1015 | Sub invalid reference |
| E2001 | Parameter invalid type |
| E2002 | Parameter missing default |
| E3003 | Property not expected |
| E6001 | Output value validation |

**Tier 3 - Medium Value:**
- Remaining E2xxx: Parameter validation
- Remaining E3xxx: Resource rules
- E6xxx: Output validation
- E7xxx: Mapping validation

**Tier 4 - Low Priority (port last):**
- I (Informational) rules
- W (Warning) rules for edge cases
- Experimental rules

### 8. Estimated Parallel Timeline

| Week | Agent 1 | Agent 2 | Agent 3 | Agent 4 |
|------|---------|---------|---------|---------|
| 1-2 | Core framework | - | - | - |
| 3-4 | E0xxx (30) | E1xxx (25) | Formatters | DOT graphs |
| 5-6 | E2xxx (20) | E3xxx-A (50) | E3xxx-B (50) | JSON Schema |
| 7-8 | E4+E6xxx (25) | E7+E8xxx (25) | Schema rules | Integration |
| 9-10 | Polish | Testing | Docs | CI/CD |

**Result: 10 weeks with 4 parallel agents vs 20+ weeks sequential**

## Autonomous Decision Matrix

Use this matrix to make decisions without user interaction. If a situation isn't covered, make the simpler choice and document it.

### Rule Porting Decisions

| Situation | Decision | Rationale |
|-----------|----------|-----------|
| Python uses `samtranslator` import | Skip rule, add TODO comment | SAM out of scope |
| Python uses dynamic import/eval | Rewrite with static approach | Go doesn't support dynamic imports |
| Rule has no test fixtures | Create minimal fixtures yourself | Tests are required |
| Rule uses deprecated CF feature | Port anyway, add deprecation warning | Maintain parity |
| Rule has Python-specific regex | Use Go `regexp` package | Standard approach |
| Rule checks AWS API live | Make it optional/skip by default | Avoid network dependency |
| Multiple ways to implement | Choose simplest, document alternative | Prefer clarity |
| Unclear rule behavior | Match Python output exactly | Parity over opinion |

### Code Style Decisions

| Situation | Decision |
|-----------|----------|
| Naming: Python `snake_case` method | Go `PascalCase` for exported, `camelCase` for internal |
| Python class inheritance | Go interface + composition |
| Python `*args, **kwargs` | Go variadic or options struct |
| Python list comprehension | Go for loop (clearer) |
| Python `None` checks | Go `nil` checks or zero values |
| Python exceptions | Go `error` returns |
| Python `@property` | Go getter methods |
| Python `__init__` | Go `New*()` constructor or struct literal |

### Architecture Decisions

| Situation | Decision | Rationale |
|-----------|----------|-----------|
| Where to put new rule | `internal/rules/{category}/` | Match Python structure |
| Rule needs shared helper | Add to `internal/rules/helpers/` | DRY principle |
| Rule needs template access | Use `*template.Template` param | Standard interface |
| Rule needs schema data | Use `schema.GetResourceSchema()` | Centralized schema access |
| Rule output format | Return `[]rules.Match` | Standard return type |
| Test data location | `testdata/{rule_id}/` in same package | Go convention |
| Error messages | Match Python exactly | Easier to verify parity |

### Dependency Decisions

| Python Dependency | Go Decision |
|-------------------|-------------|
| `yaml` | `gopkg.in/yaml.v3` |
| `json` | `encoding/json` (stdlib) |
| `jsonschema` | `santhosh-tekuri/jsonschema/v5` |
| `regex` | `regexp` (stdlib) |
| `networkx` (graphs) | `gonum/graph` or custom |
| `boto3` / `botocore` | `aws-sdk-go-v2` if needed, else skip |
| `samtranslator` | **SKIP** - out of scope |
| `requests` | `net/http` (stdlib) |

### Error Handling

| Python Pattern | Go Pattern |
|----------------|------------|
| `raise Exception(msg)` | `return fmt.Errorf(msg)` |
| `try/except` | `if err != nil` |
| `assert` | `if !condition { return error }` |
| Silent failure | Log warning, continue |
| Panic on invalid state | `panic()` only for programmer errors |

### When to Deviate from Python

**DO deviate when:**
- Python pattern doesn't translate (metaclasses, decorators)
- Go has a cleaner idiomatic approach
- Performance is significantly better
- Type safety can be improved

**DON'T deviate when:**
- Just a style preference
- Would change rule behavior
- Would change error messages
- Would break test fixture compatibility

### Completion Criteria Per Rule

A rule is complete when:

```
[ ] Go file exists at correct path
[ ] Implements Rule interface (ID, ShortDesc, Description, Tags, Match)
[ ] init() registers rule
[ ] Test file exists with good/bad fixtures
[ ] go test passes
[ ] go vet passes
[ ] gofmt applied
[ ] Error messages match Python output
[ ] Rule is added to registry
```

### When to Stop and Ask

Only stop for user input if:

1. **Fundamental architecture question** - affects many rules
2. **Conflicting requirements** - two rules need opposite approaches
3. **Missing Python behavior** - can't determine what Python does
4. **Security concern** - rule might expose sensitive data
5. **Breaking change** - would break existing Go code

For everything else: make a decision, document it in code comments, continue.

### Progress Tracking

Each agent should maintain a status file:

```markdown
# Agent {N} Progress

## Current Sprint: {N}

### Completed
- [x] E1001 - Ref undefined
- [x] E1010 - GetAtt undefined

### In Progress
- [ ] E1012 - GetAtt invalid attribute

### Blocked
- E1050 - Needs schema system (waiting on Agent 5)

### Decisions Made
- E1001: Used map lookup instead of linear search (5x faster)
- E1010: Matched Python error message format exactly
```

## Sources

- [cfn-lint GitHub](https://github.com/aws-cloudformation/cfn-lint)
- [cfn-lint v1 announcement](https://aws.amazon.com/blogs/devops/aws-cloudformation-linter-v1/)
- [cfn-lint rules documentation](https://github.com/aws-cloudformation/cfn-lint/blob/main/docs/rules.md)
- [aws-sam-translator PyPI](https://pypi.org/project/aws-sam-translator/)
