# Quick Start

Get started with `wetwire-agent` for AI-assisted infrastructure design and testing.

## Installation

```bash
go install github.com/lex00/wetwire/go/wetwire-agent/cmd/wetwire-agent@latest
```

## Overview

`wetwire-agent` provides two main workflows:

1. **Interactive Design** - A human developer describes infrastructure needs, and an AI Runner agent generates code
2. **Automated Testing** - AI Developer personas simulate different user types to test the Runner's capabilities

---

## Interactive Design Session

Start an interactive session to design infrastructure:

```bash
wetwire-agent design "I need a bucket for logs"
```

The Runner agent will:
1. Ask clarifying questions about your requirements
2. Generate wetwire-aws code
3. Run linting to ensure code quality
4. Build the CloudFormation template

### Example Session

```
$ wetwire-agent design "I need a bucket for logs"

Starting design session...
Prompt: I need a bucket for logs

Runner: I'll help you create an S3 bucket for logs. A few questions:

1. Do you need versioning enabled for the logs?
2. Should the bucket have lifecycle rules to expire old logs?
3. What encryption do you prefer: SSE-S3 or SSE-KMS?

You: Yes to versioning, expire after 90 days, SSE-S3 is fine

Runner: Creating your log bucket configuration...

[Generating storage.go]
[Running lint...]
[Building template...]

Session complete! Results written to ./human/
Generated files: [storage.go]
```

---

## Automated Testing

Test the Runner's capabilities with different developer personas:

```bash
# Test with a beginner persona
wetwire-agent test --persona beginner --prompt "I need a bucket"

# Test with an expert persona
wetwire-agent test --persona expert --prompt "S3 with SSE-KMS and versioning"

# Test with all personas
wetwire-agent test --persona all --prompt "log storage bucket"
```

### Available Personas

| Persona | Description |
|---------|-------------|
| `beginner` | New to AWS, uses vague language, needs guidance |
| `intermediate` | Familiar with AWS, knows basic concepts |
| `expert` | AWS expert, uses technical terminology |
| `terse` | Gives minimal information, one-word answers |
| `verbose` | Provides excessive detail, long explanations |

### Viewing Persona Details

```bash
# List all personas
wetwire-agent list personas

# Show detailed descriptions
wetwire-agent list personas --verbose
```

---

## Running Scenarios

Scenarios are predefined test cases with expected outputs:

```bash
# Run a scenario
wetwire-agent run-scenario ./scenarios/s3_log_bucket

# Run with a specific persona and generate code
wetwire-agent run-scenario ./scenarios/s3_log_bucket --persona beginner --generate

# Run with all personas and save results
wetwire-agent run-scenario ./scenarios/s3_log_bucket --persona all --save-results
```

### Scenario Structure

```
scenarios/
└── s3_log_bucket/
    ├── prompts/
    │   ├── beginner.md    # Prompt for beginner persona
    │   └── expert.md      # Prompt for expert persona
    ├── expected/
    │   └── storage.go     # Reference implementation
    └── results/
        └── beginner/
            ├── RESULTS.md
            └── session.json
```

---

## Scoring System

Each session is scored on 5 dimensions (0-3 each):

| Dimension | Description |
|-----------|-------------|
| Completeness | Are all requested resources generated? |
| Lint Quality | Does the code pass linting? |
| Code Quality | Is the code idiomatic and well-structured? |
| Output Validity | Does the template validate? |
| Question Efficiency | Were questions relevant and minimal? |

### Score Thresholds

| Score Range | Rating |
|-------------|--------|
| 0-5 | Failure |
| 6-9 | Partial |
| 10-12 | Success |
| 13-15 | Excellent |

### Viewing Results

Results are written to the output directory:

```
output/
└── beginner/
    ├── RESULTS.md       # Human-readable summary
    ├── session.json     # Full session data
    └── score.json       # Detailed scoring
```

---

## CLI Commands

```bash
# Design (interactive)
wetwire-agent design "prompt" [-o output_dir]

# Test (automated)
wetwire-agent test --persona <name> --prompt "prompt" [-o output_dir]

# Run scenario
wetwire-agent run-scenario <path> [--persona <name>] [--generate] [--save-results]

# List resources
wetwire-agent list personas [--verbose]
wetwire-agent list domains
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | API key for Claude (required for AI features) |

---

## Next Steps

- See [Personas](PERSONAS.md) for detailed persona descriptions
- See [Scoring](SCORING.md) for the complete scoring rubric
- See [Scenarios](SCENARIOS.md) for creating test scenarios
