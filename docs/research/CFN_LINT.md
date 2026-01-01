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

## Sources

- [cfn-lint GitHub](https://github.com/aws-cloudformation/cfn-lint)
- [cfn-lint v1 announcement](https://aws.amazon.com/blogs/devops/aws-cloudformation-linter-v1/)
- [cfn-lint rules documentation](https://github.com/aws-cloudformation/cfn-lint/blob/main/docs/rules.md)
- [aws-sam-translator PyPI](https://pypi.org/project/aws-sam-translator/)
