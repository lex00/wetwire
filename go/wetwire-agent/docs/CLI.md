# CLI Reference

The `wetwire-agent` command provides tools for AI-assisted infrastructure design and testing.

## Quick Reference

| Command | Description |
|---------|-------------|
| `wetwire-agent design` | Start an interactive design session |
| `wetwire-agent test` | Run automated test with AI personas |
| `wetwire-agent run-scenario` | Run a predefined test scenario |
| `wetwire-agent list` | List available personas and domains |

```bash
wetwire-agent --help     # Show help
```

---

## design

Start an interactive design session where you describe infrastructure needs and the AI Runner generates code.

```bash
# Basic usage
wetwire-agent design "I need a bucket for logs"

# Specify output directory
wetwire-agent design "I need a bucket for logs" -o ./output
```

### Options

| Option | Description |
|--------|-------------|
| `PROMPT` | Initial infrastructure requirement |
| `-o, --output DIR` | Output directory for generated files (default: `.`) |

### How It Works

1. You provide an initial prompt describing your infrastructure needs
2. The Runner agent asks clarifying questions
3. You answer questions interactively
4. Runner generates wetwire-aws code
5. Code is linted and template is built
6. Results are saved to the output directory

### Output

```
output/
└── human/
    ├── RESULTS.md       # Session summary
    ├── session.json     # Full session data
    └── storage.go       # Generated code
```

---

## test

Run automated tests with AI developer personas.

```bash
# Test with a specific persona
wetwire-agent test --persona beginner --prompt "I need a bucket"

# Test with all personas
wetwire-agent test --persona all --prompt "log storage bucket"

# Specify output directory
wetwire-agent test --persona expert --prompt "S3 with SSE-KMS" -o ./results
```

### Options

| Option | Description |
|--------|-------------|
| `-p, --persona NAME` | Persona to use (beginner, intermediate, expert, terse, verbose, all) |
| `--prompt TEXT` | Initial prompt for the developer (required) |
| `-o, --output DIR` | Output directory for results (default: `.`) |

### Personas

| Persona | Behavior |
|---------|----------|
| `beginner` | New to AWS, vague requirements, needs guidance |
| `intermediate` | Familiar with AWS basics, gives reasonable answers |
| `expert` | Uses technical terminology, provides detailed specs |
| `terse` | Minimal responses, one-word answers |
| `verbose` | Excessive detail, long explanations |

### Output

Results are written per-persona:

```
results/
├── beginner/
│   ├── RESULTS.md
│   ├── session.json
│   └── score.json
├── intermediate/
│   └── ...
└── expert/
    └── ...
```

---

## run-scenario

Run a predefined test scenario with expected outputs.

```bash
# Validate expected directory only
wetwire-agent run-scenario ./scenarios/s3_log_bucket

# Generate with a specific persona
wetwire-agent run-scenario ./scenarios/s3_log_bucket --persona beginner --generate

# Generate with all personas and save results
wetwire-agent run-scenario ./scenarios/s3_log_bucket --persona all --generate --save-results
```

### Options

| Option | Description |
|--------|-------------|
| `PATH` | Path to scenario directory (required) |
| `-p, --persona NAME` | Persona to use (or 'all') |
| `--generate` | Generate code using AI (otherwise just validate expected/) |
| `--save-results` | Save results to scenario results/ directory |

### Scenario Structure

```
scenarios/
└── s3_log_bucket/
    ├── prompts/
    │   ├── beginner.md      # Prompt for beginner persona
    │   ├── intermediate.md  # Prompt for intermediate persona
    │   └── expert.md        # Prompt for expert persona
    ├── expected/
    │   └── storage.go       # Reference implementation
    └── results/
        └── beginner/
            ├── RESULTS.md
            ├── session.json
            └── score.json
```

### Scoring

Each scenario run is scored on 5 dimensions (0-3 each, max 15):

| Dimension | Description |
|-----------|-------------|
| Completeness | All requested resources generated |
| LintQuality | Code passes linting |
| CodeQuality | Idiomatic, well-structured code |
| OutputValidity | Valid CloudFormation template |
| QuestionEfficiency | Minimal, relevant questions |

---

## list

List available resources.

### list personas

```bash
# List all personas
wetwire-agent list personas

# Show detailed descriptions
wetwire-agent list personas --verbose
```

**Output:**
```
Available Personas:

  beginner      Developer new to AWS and infrastructure
  intermediate  Developer with basic AWS knowledge
  expert        Experienced AWS architect
  terse         Developer who gives minimal responses
  verbose       Developer who provides excessive detail

Use --verbose for detailed descriptions
```

### list domains

```bash
wetwire-agent list domains
```

**Output:**
```
Available Domains:

  aws         wetwire-aws     AWS CloudFormation resources
```

---

## Scoring Details

### Dimension Ratings (0-3)

**Completeness:**
- 0: Missing most resources
- 1: Some resources missing
- 2: All resources, minor issues
- 3: All resources, correct configuration

**Lint Quality:**
- 0: Many lint errors
- 1: Some lint errors
- 2: Warnings only
- 3: Clean lint pass

**Code Quality:**
- 0: Major structural issues
- 1: Works but not idiomatic
- 2: Good structure, minor improvements possible
- 3: Excellent, idiomatic code

**Output Validity:**
- 0: Invalid template
- 1: Template has errors
- 2: Template has warnings
- 3: Valid, no issues

**Question Efficiency:**
- 0: Excessive or irrelevant questions
- 1: Too many questions
- 2: Appropriate questions
- 3: Minimal, highly relevant questions

### Thresholds

| Score | Rating | Description |
|-------|--------|-------------|
| 0-5 | Failure | Significant issues, needs improvement |
| 6-9 | Partial | Some issues, mostly functional |
| 10-12 | Success | Good results, minor improvements |
| 13-15 | Excellent | Outstanding performance |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | API key for Claude (required for AI features) |

---

## Examples

### Complete Workflow

```bash
# 1. List available personas
wetwire-agent list personas

# 2. Run test with beginner persona
wetwire-agent test --persona beginner --prompt "I need a bucket for logs"

# 3. Check results
cat beginner/RESULTS.md

# 4. Run scenario with all personas
wetwire-agent run-scenario ./scenarios/s3_log_bucket --persona all --generate --save-results
```

### CI/CD Integration

```bash
#!/bin/bash
# test-scenarios.sh

for scenario in scenarios/*/; do
    echo "Running: $scenario"
    wetwire-agent run-scenario "$scenario" --persona all --generate --save-results

    # Check for failures
    if [ $? -ne 0 ]; then
        echo "FAILED: $scenario"
        exit 1
    fi
done

echo "All scenarios passed!"
```

---

## See Also

- [Quick Start](QUICK_START.md) - Get started quickly
- [Personas](PERSONAS.md) - Detailed persona descriptions
- [Scoring](SCORING.md) - Complete scoring rubric
