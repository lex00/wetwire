# Wetwire Agent Research

**Status**: Active development
**Purpose**: Document the design decisions and architecture of `wetwire-agent` for testing and design orchestration.
**Scope**: **Orchestration only** - coordinates AI/human agents to generate wetwire packages; does not generate infrastructure directly.
**Recommendation**: **Viable** - Two-agent workflow enables both automated testing and interactive design.

---

## Executive Summary

`wetwire-agent` is an **orchestration package** - it coordinates a Developer/Runner workflow to generate wetwire infrastructure packages. It does not generate infrastructure directly.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  wetwire-agent (orchestration)         Domain packages (synthesis)      │
│                                                                          │
│  [Developer] ──► [Runner] ──► wetwire-aws/gcp/azure                     │
│  (human/AI)      (AI+CLI)        (generates templates)                  │
│                      │                    ↓                              │
│                      └──────► Package + RESULTS.md                       │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key insight:**
- Same workflow for **testing** (AI Developer) and **production** (human Developer)
- Runner has CLI access; Developer provides intent
- Personas enable systematic testing of edge cases

---

## Vision

**wetwire-agent unifies testing and design.** The same two-agent workflow serves both purposes - only the Developer role changes.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        wetwire-agent (this project)                      │
│                                                                          │
│   TESTING MODE                        PRODUCTION MODE                    │
│   ┌──────────────┐                    ┌──────────────┐                   │
│   │  Developer   │                    │  Developer   │                   │
│   │  = AI Agent  │                    │  = Human     │                   │
│   │  (persona)   │                    │  (engineer)  │                   │
│   └──────┬───────┘                    └──────┬───────┘                   │
│          │                                   │                           │
│          ▼                                   ▼                           │
│   ┌──────────────────────────────────────────────────────────┐          │
│   │                      Runner Agent                         │          │
│   │  - Has CLI access (wetwire-aws lint, build, etc.)        │          │
│   │  - Generates package code                                 │          │
│   │  - Asks Developer for clarification                       │          │
│   │  - Writes RESULTS.md                                      │          │
│   └──────────────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Core principles:**
1. **Same workflow, different actors** - Testing uses AI Developer, production uses human
2. **Runner generates code** - Not templates, actual wetwire package source files
3. **Personas test edge cases** - beginner, expert, terse, verbose, etc.
4. **Scoring enables CI** - 0-15 rubric becomes quality gate

---

## Architecture

### Two-Agent Pattern

| Role | Testing | Production | Access |
|------|---------|------------|--------|
| **Developer** | AI (persona) | Human | None - just provides intent |
| **Runner** | AI + CLI | AI + CLI | Full CLI access |

### Why Two Agents?

**Single-agent approaches fail because:**
- AI generating infrastructure with no validation = hallucinations
- Human writing everything = no AI assistance

**Two-agent solves this:**
- Developer (human or AI) provides **what** they want
- Runner (AI + CLI) provides **how** to build it
- Runner has feedback loop via `wetwire-aws lint`

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Orchestrator                                   │
│                    (coordinates communication)                           │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────────────────┐
        │                          │                                       │
        ▼                          ▼                                       ▼
┌───────────────┐         ┌───────────────┐                    ┌───────────────┐
│   Developer   │◄───────►│    Runner     │───────────────────►│   Artifacts   │
│               │         │               │                    │               │
│ Provides:     │         │ Uses:         │                    │ Outputs:      │
│ - Intent      │         │ - wetwire-aws │                    │ - Package/    │
│ - Answers     │         │ - lint, build │                    │ - RESULTS.md  │
│               │         │ - cfn-lint    │                    │ - score.json  │
└───────────────┘         └───────────────┘                    └───────────────┘
```

---

## Generated Package Pattern

The Runner generates wetwire packages using the **decorator-free wrapper pattern**:

```python
# generated/__init__.py
from wetwire_aws.loader import setup_resources
setup_resources(__file__, __name__, globals())

# generated/storage.py
from . import *

class LogBucket:
    resource: s3.Bucket
    bucket_name = "my-logs"
    versioning_configuration = BucketVersioning

class BucketVersioning:
    resource: s3.Bucket.VersioningConfiguration
    status = s3.BucketVersioningStatus.ENABLED
```

**Key patterns:**
1. **`from . import *`** - Single import brings all service modules
2. **`resource:` annotation** - Auto-decorated by `setup_resources()`
3. **No explicit `@wetwire_aws`** - Decorator is invisible to users
4. **Wrapper classes for properties** - Even inline types use wrapper pattern

---

## Personas

Personas configure Developer behavior during testing. Each tests different Runner capabilities.

| Persona | Prompt Style | Expected Runner Behavior |
|---------|-------------|--------------------------|
| **beginner** | Vague, uncertain | Make safe defaults, explain choices |
| **intermediate** | Some knowledge | Balance questions with assumptions |
| **expert** | Precise requirements | Be precise, minimal explanation |
| **terse** | Minimal words | Just generate, no explanation needed |
| **verbose** | Over-explains | Filter signal from noise |

### Example Prompts by Persona

**beginner:**
> "I need a bucket for logs, not sure what settings I need. Should it be encrypted? What about versioning?"

**expert:**
> "S3 bucket with AES-256 SSE-S3, block all public access, versioning enabled, lifecycle rule to transition to Glacier after 90 days."

**terse:**
> "log bucket"

---

## Workflow Phases

### Phase 1: Initialization
1. Developer provides natural language prompt
2. Runner parses requirements
3. Runner initializes new package via `wetwire-aws init`

### Phase 2: Clarification
Runner asks Developer questions when intent is unclear:
```
Runner: "Should the bucket have versioning enabled?"
Developer: "Yes, I want to keep old versions for 30 days"
```

### Phase 3: Implementation
Runner creates resource files:
- Writes source files with `resource:` annotated classes
- Uses wrapper pattern for all resources and properties
- Imports via `from . import *`

### Phase 4: Lint Cycles (max 3)
For each cycle:
1. Run `wetwire-aws lint`
2. If issues found: analyze and fix
3. If intent unclear: ask Developer
4. If no issues or max cycles: exit loop

### Phase 5: Validation
1. Run `wetwire-aws build` to generate template
2. Run `cfn-lint` on output
3. Write RESULTS.md with full session log

---

## Scoring Rubric

Each session scored on 5 dimensions (0-3 scale):

| Dimension | 3 | 2 | 1 | 0 |
|-----------|---|---|---|---|
| **Completeness** | All resources | Most resources | Some resources | None |
| **Lint Quality** | Pass first try | Pass in 1-2 cycles | Pass in 3 cycles | Never pass |
| **Code Quality** | Idiomatic patterns | Good patterns | Poor patterns | Invalid |
| **Output Validity** | cfn-lint clean | Warnings only | Errors | No output |
| **Question Efficiency** | 0-2 questions | 3-4 questions | 5+ questions | - |

**Score thresholds:**
- **0-5**: Failure (CI fails)
- **6-9**: Partial (needs review)
- **10-12**: Success
- **13-15**: Excellent

---

## Scenario Organization

Scenarios are test cases organized by complexity:

```
tests/domains/aws/scenarios/
├── s3_log_bucket/           # Simple
│   ├── prompts/
│   │   ├── beginner.md
│   │   ├── expert.md
│   │   └── terse.md
│   ├── expected/            # Reference implementation
│   │   ├── __init__.py
│   │   └── storage.py
│   └── results/             # Test outputs
│       ├── beginner/
│       └── expert/
├── vpc_private/             # Medium
└── full_stack_app/          # Complex
```

### Difficulty Levels

| Level | Cycles | Questions | Example |
|-------|--------|-----------|---------|
| **Simple** | 0-1 | 0-1 | Single S3 bucket |
| **Medium** | 1-2 | 1-3 | VPC with subnets |
| **Complex** | 2-3 | 3+ | Full application stack |
| **Adversarial** | May fail | N/A | "Make it secure" (no context) |

---

## CLI Commands

```bash
# Validate existing expected packages (no AI needed)
wetwire-agent validate-scenarios tests/domains/aws/scenarios

# Run single scenario validation
wetwire-agent run-scenario tests/domains/aws/scenarios/s3_log_bucket

# Run with AI generation
wetwire-agent run-scenario <path> --generate --persona beginner

# Run all personas
wetwire-agent run-scenario <path> --persona all --save-results

# List available resources
wetwire-agent list domains
wetwire-agent list personas
```

---

## Virtuous Cycle

The workflow creates feedback for framework improvement:

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│   Run Scenarios ──► Find Failures ──► Improve Framework ──┘
│         │
│         ├── Add lint rules for common mistakes
│         ├── Improve error messages
│         ├── Add examples/presets
│         └── Fix code generation bugs
```

RESULTS.md captures improvement suggestions from each session.

---

## Integration with Domain Packages

wetwire-agent works with any wetwire domain package:

| Domain | CLI Tool | Output |
|--------|----------|--------|
| AWS | `wetwire-aws` | CloudFormation JSON/YAML |
| GCP | `wetwire-gcp` | Config Connector YAML |
| Azure | `wetwire-azure` | ARM JSON |
| K8s | `wetwire-k8s` | Kubernetes YAML |

The Runner uses domain-specific CLI tools but follows the same workflow pattern.

---

## Known Limitations

### In Scope
| Limitation | How Addressed |
|------------|---------------|
| AI hallucinations | Lint cycle catches invalid resources |
| Vague requirements | Clarification phase with Developer |
| Persona variability | Scoring rubric normalizes expectations |

### Out of Scope
| Limitation | Notes |
|------------|-------|
| Deployment | Use domain tools (`aws cloudformation deploy`) |
| Multi-cloud | Each domain handled separately |
| Cost estimation | Not part of generation workflow |

---

## Viability Assessment

| Factor | Assessment | Notes |
|--------|------------|-------|
| Testing coverage | **Good** | Personas cover edge cases |
| Production utility | **Good** | Same workflow with human Developer |
| Lint integration | **Excellent** | Catches issues before completion |
| CI integration | **Good** | Scoring becomes quality gate |
| Framework feedback | **Excellent** | RESULTS.md captures improvements |

---

## Conclusion

**Status: Viable.**

wetwire-agent demonstrates that **two-agent orchestration unifies testing and production workflows**:

| Factor | Assessment |
|--------|------------|
| **Architecture** | Two-agent pattern (Developer + Runner) |
| **Testing** | Personas enable systematic edge case testing |
| **Production** | Same workflow with human Developer |
| **Integration** | Works with any wetwire domain package |
| **Feedback loop** | RESULTS.md captures framework improvements |

**The key insight:** By making the Developer role interchangeable (AI for testing, human for production), we get both automated regression testing and interactive design from the same codebase.
