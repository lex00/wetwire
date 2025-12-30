# wetwire-agent

Testing and design orchestration for wetwire domain packages.

## Overview

wetwire-agent provides a two-agent workflow for:

1. **Interactive Design** - Human developer works with AI runner to create infrastructure packages
2. **Automated Testing** - AI developer (persona) tests AI runner's ability to generate correct packages

## Installation

```bash
pip install wetwire-agent
```

This automatically installs domain packages (wetwire-aws) as dependencies.

## Quick Start

### List Available Resources

```bash
# List domains
wetwire-agent list domains

# List personas
wetwire-agent list personas

# List AWS prompts
wetwire-agent list prompts --domain aws
```

### Interactive Design Session

```bash
# Start design session for AWS
wetwire-agent design --domain aws
```

### Automated Testing

```bash
# Test AWS with beginner persona
wetwire-agent test --domain aws --persona beginner

# Test all domains
wetwire-agent test --all

# Test specific difficulty
wetwire-agent test --domain aws --difficulty simple
```

## Architecture

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

## Personas

Personas configure Developer behavior during testing:

| Persona | Behavior | Tests |
|---------|----------|-------|
| beginner | Vague requirements, defers to suggestions | Handling ambiguity |
| intermediate | Mixed clarity, asks clarifying questions | Back-and-forth dialogue |
| expert | Precise requirements, corrects mistakes | Meeting high standards |
| terse | Minimal responses ("yes", "no") | Working without guidance |
| verbose | Over-explains, adds tangents | Filtering signal from noise |

## Scoring

Sessions are scored on 5 dimensions (0-3 scale):

| Dimension | 0 | 1 | 2 | 3 |
|-----------|---|---|---|---|
| Completeness | Failed | Missing resources | Most resources | All resources |
| Lint Quality | Never passed | Passed after 3 | Passed after 1-2 | Passed first try |
| Code Quality | Invalid syntax | Poor patterns | Good patterns | Idiomatic |
| Output Validity | Invalid | Valid with errors | Valid with warnings | Clean |
| Question Efficiency | 5+ questions | 3-4 questions | 1-2 questions | 0 (when appropriate) |

**Overall Score:** 0-15

- 0-5: Failure
- 6-9: Partial success
- 10-12: Success
- 13-15: Excellent

## Documentation

See [docs/AGENT_WORKFLOW.md](docs/AGENT_WORKFLOW.md) for the complete specification.

## License

MIT
