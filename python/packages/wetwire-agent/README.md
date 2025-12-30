# wetwire-agent

Testing and design orchestration for wetwire domain packages.

## Overview

Two-agent workflow for:
1. **Interactive Design** - Human developer + AI runner creates infrastructure
2. **Automated Testing** - AI developer (persona) + AI runner tests generation

## Installation

```bash
pip install wetwire-agent
```

## Claude Code Skill

When using Claude Code in this repository, you can run scenarios interactively:

```
/run-scenario tests/domains/aws/scenarios/s3_log_bucket
/run-scenario tests/domains/aws/scenarios/s3_log_bucket --persona expert
/run-scenario all --persona beginner
```

Claude will act as the Runner agent:
1. Read the scenario prompt
2. Generate a wetwire-aws package
3. Run `wetwire-aws lint` validation
4. Build CloudFormation template
5. Run `cfn-lint` validation
6. Save results to `<scenario>/results/<persona>/`

## CLI Commands

```bash
# Run a scenario (validates expected output)
uv run wetwire-agent run-scenario tests/domains/aws/scenarios/s3_log_bucket

# Run scenario with AI generation
uv run wetwire-agent run-scenario <path> --generate --persona beginner

# Run all personas
uv run wetwire-agent run-scenario <path> --persona all --save-results

# Validate all scenarios (for CI)
uv run wetwire-agent validate-scenarios tests/domains/aws/scenarios

# List resources
uv run wetwire-agent list domains
uv run wetwire-agent list personas
```

## Personas

| Persona | Behavior | Tests |
|---------|----------|-------|
| beginner | Vague, defers to suggestions | Handling ambiguity |
| intermediate | Mixed clarity, asks questions | Back-and-forth dialogue |
| expert | Precise, corrects mistakes | Meeting high standards |
| terse | Minimal responses | Working without guidance |
| verbose | Over-explains | Filtering signal from noise |

## Scoring (0-15)

| Dimension | Description |
|-----------|-------------|
| Completeness | All resources created (0-3) |
| Lint Quality | Passes on first try (0-3) |
| Code Quality | Idiomatic patterns (0-3) |
| Output Validity | Clean CloudFormation (0-3) |
| Question Efficiency | Minimal questions (0-3) |

- **0-5**: Failure
- **6-9**: Partial success
- **10-12**: Success
- **13-15**: Excellent

## Documentation

See [docs/AGENT_WORKFLOW.md](docs/AGENT_WORKFLOW.md) for the complete specification.

## License

MIT
