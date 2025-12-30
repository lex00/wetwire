# Agent Workflow: Design and Test Unification

**Version:** 0.2
**Status:** Draft
**Last Updated:** 2024-12-26

> **This is the language-agnostic specification.** For implementation details, see:
> - Python: [python/docs/PYTHON_AGENT_WORKFLOW.md](../../python/docs/PYTHON_AGENT_WORKFLOW.md)

## Overview

Wetwire uses a two-agent workflow for both **testing implementations** and **designing infrastructure**. The same workflow serves both purposes — the only difference is whether the "Developer" role is played by an AI agent (testing) or a human (production use).

## Core Insight

```
┌─────────────────────────────────────────────────────────────┐
│                    SAME WORKFLOW                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [Persona + Prompt] ───► [Runner Agent] ───► [Package]     │
│         │                      │                  │         │
│         ▼                      ▼                  ▼         │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│   │  TESTING     │    │  BOTH        │    │  BOTH        │  │
│   │  Developer   │    │  Questions/  │    │  RESULTS.md  │  │
│   │  = AI Agent  │    │  Answers     │    │  + Package   │  │
│   ├──────────────┤    │              │    │              │  │
│   │  PRODUCTION  │    │              │    │              │  │
│   │  Developer   │    │              │    │              │  │
│   │  = Human     │    │              │    │              │  │
│   └──────────────┘    └──────────────┘    └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture

### Components

```
                    ┌─────────────────────────────────────────┐
                    │           Orchestrator                  │
                    │     (design / test commands)            │
                    └─────────────────┬───────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
     ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
     │    Developer    │    │     Runner      │    │    Artifacts    │
     │                 │    │                 │    │                 │
     │ Testing: AI     │◄──►│  AI Agent with  │───►│  Package/       │
     │ Prod: Human     │    │  CLI tools      │    │  RESULTS.md     │
     └─────────────────┘    └────────┬────────┘    └─────────────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │  Domain CLI     │
                            │  (aws, gcp,     │
                            │   k8s, etc.)    │
                            └─────────────────┘
```

### Developer Agent

- Represents the user with a goal
- Provides natural language requirements
- Answers questions about intent
- Does NOT have CLI access

**In testing:** AI agent configured with a persona
**In production:** Human user

### Runner Agent

- Has full access to wetwire CLI tools
- Creates packages, writes code, runs linter
- Asks Developer for clarification when needed
- Writes RESULTS.md documenting the process

### Orchestrator

- Coordinates communication between Developer and Runner
- Routes messages back and forth
- Enforces maximum cycles (default: 3 lint cycles)
- Collects final outputs

---

## Workflow Phases

### Phase 1: Initialization

1. Developer provides natural language prompt
2. Runner parses requirements
3. Runner initializes new package
4. Runner plans resources needed

### Phase 2: Clarification

Runner asks Developer questions when intent is unclear:

```
Runner: "Should the VPC use public subnets with an Internet Gateway,
        or private subnets with a NAT Gateway?"

Developer: "Private subnets with NAT Gateway. I want the instances
           to not be directly accessible from the internet."
```

### Phase 3: Implementation

Runner creates resource files:
- Writes source files with wetwire-decorated classes
- Imports appropriate domain modules
- Defines parameters, resources, outputs

### Phase 4: Lint Cycles (max 3)

For each cycle:

1. Run domain linter
2. If issues found:
   - Analyze and fix issues
   - If intent unclear, ask Developer
3. If no issues or max cycles: exit loop

### Phase 5: Completion

1. Generate type stubs (if applicable)
2. Write RESULTS.md
3. Return package path

---

## Personas

Personas configure Developer behavior during testing. Each persona tests different Runner capabilities.

| Persona | Behavior | Tests |
|---------|----------|-------|
| [beginner](../personas/beginner.md) | Vague requirements, defers to suggestions | Handling ambiguity |
| [intermediate](../personas/intermediate.md) | Mixed clarity, asks clarifying questions | Back-and-forth dialogue |
| [expert](../personas/expert.md) | Precise requirements, corrects mistakes | Meeting high standards |
| [terse](../personas/terse.md) | Minimal responses ("yes", "no") | Working without guidance |
| [verbose](../personas/verbose.md) | Over-explains, adds tangents | Filtering signal from noise |

See [personas/](../personas/) for detailed persona definitions.

---

## RESULTS.md Format

Every session produces a RESULTS.md documenting the process:

```markdown
# Package Generation Results

**Prompt:** "Build an autoscaled EC2 instance in a private VPC"
**Package:** ec2_private_vpc
**Date:** 2024-12-26
**Persona:** intermediate (if testing)

## Summary

Created a stack with:
- VPC with 2 private subnets across 2 AZs
- NAT Gateway for outbound internet access
- Auto Scaling Group with instances
- Security Group allowing SSH from bastion

## Lint Cycles

### Cycle 1
**Issues Found:** 3
- Rule001: Description of issue
- Rule002: Description of issue
- Rule003: Description of issue

**Actions Taken:**
- Fixed issue 1
- Fixed issue 2
- Split into multiple files

### Cycle 2
**Issues Found:** 0
- All lint checks passed

## Questions Asked

1. **Runner:** "Public or private subnets?"
   **Developer:** "Private with NAT Gateway"

2. **Runner:** "What instance type?"
   **Developer:** "t3.medium, but make it a parameter"

## Framework Improvement Suggestions

1. Add lint rule for specific pattern
2. Add example to documentation
3. Improve error message for common mistake
```

---

## Scoring Rubric

Each session is scored on 5 dimensions (0-3 scale):

| Dimension | 0 | 1 | 2 | 3 |
|-----------|---|---|---|---|
| **Completeness** | Failed to produce package | Missing resources | Most resources | All resources |
| **Lint Quality** | Never passed | Passed after 3 cycles | Passed after 1-2 | Passed first try |
| **Code Quality** | Invalid syntax | Poor patterns | Good patterns | Idiomatic |
| **Output Validity** | Invalid | Valid with errors | Valid with warnings | Clean |
| **Question Efficiency** | 5+ questions | 3-4 questions | 1-2 questions | 0 (when appropriate) |

**Overall Score:** 0-15
- 0-5: Failure
- 6-9: Partial success
- 10-12: Success
- 13-15: Excellent

### CI/CD Integration

Scores become quality gates:
- Score < 6: Build fails
- Score 6-9: Warning, needs review
- Score 10+: Pass

---

## Prompt Organization

Prompts are organized by difficulty:

### Simple (0-1 cycles, 0-1 questions expected)

Basic resources with clear requirements. Tests fundamental understanding.

### Medium (1-2 cycles, 1-3 questions expected)

Multi-resource stacks with some ambiguity. Tests clarification skills.

### Complex (2-3 cycles, 3+ questions expected)

Full architectures with many resources. Tests comprehensive planning.

### Adversarial (may fail, tests error handling)

Intentionally problematic prompts. Tests graceful degradation.

Examples:
- "Create a thing that stores data" (too ambiguous)
- "Make it secure" (no context)
- "EC2 with 1TB RAM" (impossible constraint)

---

## Metrics

### Per-Session Metrics

| Metric | Description |
|--------|-------------|
| `completion` | Did the session produce a valid package? |
| `cycles` | Number of lint cycles needed |
| `questions` | Number of clarification questions |
| `score` | Overall rubric score (0-15) |
| `duration` | Session duration in seconds |

### Aggregate Metrics

| Metric | Description |
|--------|-------------|
| `completion_rate` | % of sessions producing valid packages |
| `avg_cycles` | Average lint cycles across sessions |
| `avg_questions` | Average questions per session |
| `avg_score` | Average rubric score |

### Regression Detection

After framework changes:
- Run baseline prompts
- Compare metrics to previous run
- Alert if completion rate drops >10%
- Alert if avg_cycles increases >0.5

---

## Virtuous Cycle

The workflow creates a feedback loop for improvement:

```
   ┌─────────────────────────────────────────────────┐
   │                                                 │
   ▼                                                 │
Run Tests ──► Find Failures ──► Improve Framework ──┘
   │
   ├── Add lint rules
   ├── Improve documentation
   ├── Add presets/examples
   └── Fix code generation
```

When tests fail:
1. RESULTS.md captures the failure
2. Framework improvement suggestions are generated
3. Changes are made to wetwire
4. Tests are re-run to validate

---

## Implementation Requirements

Each language implementation MUST provide:

1. **CLI Commands**
   - `design` - Interactive session with human Developer
   - `test` - Automated session with AI Developer

2. **Orchestrator** - Coordinates Developer/Runner communication

3. **Persona Loader** - Loads persona definitions from `docs/personas/`

4. **Results Writer** - Generates RESULTS.md in standard format

5. **Scoring** - Implements the 0-15 rubric

6. **Prompt Library** - Domain-specific prompts organized by difficulty

---

## Related Documents

- [ARCHITECTURE.md](ARCHITECTURE.md) — Overall system architecture
- [Personas](../personas/) — Detailed persona definitions
