# wetwire-agent (Go)

AI-assisted infrastructure design and testing tool for wetwire.

## Status

**Implementation: Complete**

All core features implemented. See [Implementation Status](#implementation-status) for details.

## Overview

wetwire-agent provides two main workflows:

1. **Interactive Design** - A human developer describes infrastructure needs, and an AI Runner agent generates code
2. **Automated Testing** - AI Developer personas simulate different user types to test the Runner's capabilities

## Quick Start

### Interactive Design

```bash
wetwire-agent design "I need a bucket for logs"
```

The Runner agent will:
1. Ask clarifying questions about your requirements
2. Generate wetwire-aws code
3. Run linting to ensure code quality
4. Build the CloudFormation template

### Automated Testing

```bash
# Test with a specific persona
wetwire-agent test --persona beginner --prompt "I need a bucket"

# Test with all personas
wetwire-agent test --persona all --prompt "log storage bucket"
```

## Installation

```bash
go install github.com/lex00/wetwire/go/wetwire-agent/cmd/wetwire-agent@latest
```

**Requires:** `ANTHROPIC_API_KEY` environment variable

## CLI Commands

| Command | Status | Description |
|---------|--------|-------------|
| `design` | ✅ Complete | Interactive design session |
| `test` | ✅ Complete | Automated persona testing |
| `run-scenario` | ✅ Complete | Run predefined test scenario |
| `list personas` | ✅ Complete | List available personas |
| `list domains` | ✅ Complete | List available domains |

## Implementation Status

### What's Working

All core features are implemented:

| Feature | Status | Location |
|---------|--------|----------|
| Developer personas | ✅ | `internal/personas/` |
| 5-dimension scoring | ✅ | `internal/scoring/` |
| Session results | ✅ | `internal/results/` |
| RESULTS.md generation | ✅ | `internal/results/` |
| Developer/Runner orchestration | ✅ | `internal/orchestrator/` |
| Human developer (stdin) | ✅ | `internal/orchestrator/` |
| AI developer (personas) | ✅ | `internal/orchestrator/` |
| Anthropic SDK integration | ✅ | `internal/agents/` |
| Tool-use pattern | ✅ | `internal/agents/` |

### Personas

| Persona | Description |
|---------|-------------|
| `beginner` | New to AWS, uses vague language, needs guidance |
| `intermediate` | Familiar with AWS, knows basic concepts |
| `expert` | AWS expert, uses technical terminology |
| `terse` | Gives minimal information, one-word answers |
| `verbose` | Provides excessive detail, long explanations |

### Scoring System

Each session is scored on 5 dimensions (0-3 each, max 15):

| Dimension | Description |
|-----------|-------------|
| Completeness | Are all requested resources generated? |
| LintQuality | Does the code pass linting? |
| CodeQuality | Is the code idiomatic and well-structured? |
| OutputValidity | Does the template validate? |
| QuestionEfficiency | Were questions relevant and minimal? |

**Thresholds:**
- 0-5: Failure
- 6-9: Partial
- 10-12: Success
- 13-15: Excellent

## Package Structure

```
wetwire-agent/
├── cmd/wetwire-agent/     # CLI application
│   ├── main.go            # Entry point
│   ├── design.go          # design command
│   ├── test.go            # test command
│   ├── scenario.go        # run-scenario command
│   └── list.go            # list command
├── internal/
│   ├── personas/          # Developer persona definitions
│   ├── scoring/           # 5-dimension scoring rubric
│   ├── results/           # Session tracking, RESULTS.md
│   ├── orchestrator/      # Developer/Runner coordination
│   └── agents/            # Anthropic SDK integration
├── docs/
│   ├── QUICK_START.md
│   └── CLI.md
└── scripts/
    └── ci.sh              # Local CI script
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Orchestrator                            │
│  Coordinates Developer and Runner, tracks session results    │
└─────────────────────────────────────────────────────────────┘
                    │                       │
          ┌─────────▼─────────┐   ┌─────────▼─────────┐
          │     Developer     │   │      Runner       │
          │  (Human or AI)    │   │   (AI with tools) │
          │                   │   │                   │
          │  - Provides reqs  │   │  - Generates code │
          │  - Answers Qs     │   │  - Runs lint/build│
          │  - Persona-based  │   │  - Asks questions │
          └───────────────────┘   └───────────────────┘
                                           │
                                  ┌────────▼────────┐
                                  │  Domain CLI     │
                                  │ (wetwire-aws)   │
                                  │                 │
                                  │  - build --json │
                                  │  - lint --json  │
                                  └─────────────────┘
```

**Key Design Decisions:**

1. **CLI-Only Tool** - Not importable as a Go library
2. **Domain Agnostic** - Shells out to domain CLIs (wetwire-aws, etc.)
3. **JSON Contract** - Communicates with domain CLIs via structured JSON output
4. **Two-Agent Pattern** - Developer provides requirements, Runner generates code

## Development

```bash
# Run tests
go test -v ./...

# Run CI checks
./scripts/ci.sh

# Build CLI
go build -o wetwire-agent ./cmd/wetwire-agent
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Required for AI features |

## Documentation

- [Quick Start](docs/QUICK_START.md)
- [CLI Reference](docs/CLI.md)
- [Implementation Checklist](../../docs/research/ImplementationChecklist.md)
- [Agent Architecture](../../docs/research/AGENT.md)

## Related Packages

- [wetwire-aws](../wetwire-aws/) - AWS CloudFormation synthesis
- [wetwire-agent (Python)](../../python/packages/wetwire-agent/) - Python implementation
