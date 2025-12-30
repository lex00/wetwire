# CLAUDE.md - wetwire-agent

Instructions for Claude Code when working with this package.

## Running Scenarios

When asked to "run scenarios", "run the agent tests", or "test with all personas":

### For each scenario in `tests/domains/aws/scenarios/`:

1. **Read the persona-specific prompt**: `<scenario>/prompts/<persona>.md`

   Each persona communicates differently:
   - **beginner**: Vague, uncertain ("I need a bucket for logs, not sure what settings...")
   - **intermediate**: Some knowledge ("Create an S3 bucket, maybe with encryption?")
   - **expert**: Precise ("S3 bucket, AES-256 SSE, block all public access")
   - **terse**: Minimal ("log bucket")
   - **verbose**: Over-explains with context and concerns

2. **Generate a package** that fulfills the prompt using wetwire-aws patterns:
   ```python
   # <scenario>/generated/__init__.py
   from wetwire_aws.loader import setup_resources
   setup_resources(__file__, __name__, globals())
   ```
   ```python
   # <scenario>/generated/<resource>.py
   from . import *

   class MyResource:
       resource: <service>.<Resource>
       # properties...
   ```

3. **Run validation**:
   ```bash
   uv run wetwire-aws lint <scenario>/generated/
   uv run wetwire-aws build -m generated -f yaml > template.yaml
   uv run cfn-lint template.yaml
   ```

4. **Save results** to `<scenario>/results/<persona>/`:
   - `template.yaml` - Generated CloudFormation
   - `results.md` - Full report
   - `score.json` - Scoring breakdown
   - `generated/` - AI-generated code (only with `--generate` flag)

### Quick Commands

```bash
# Validate existing expected packages (no AI needed)
uv run wetwire-agent validate-scenarios tests/domains/aws/scenarios

# Run single scenario validation
uv run wetwire-agent run-scenario tests/domains/aws/scenarios/s3_log_bucket --save-results

# Run with AI generation
uv run wetwire-agent run-scenario tests/domains/aws/scenarios/s3_log_bucket --generate --persona beginner

# Run all personas
uv run wetwire-agent run-scenario tests/domains/aws/scenarios/s3_log_bucket --persona all --save-results
```

## Personas

Each persona has a unique prompt style AND expects a corresponding response style:

| Persona | Prompt Style | Runner Response |
|---------|-------------|-----------------|
| beginner | Vague, uncertain | Make safe defaults, explain choices |
| intermediate | Some knowledge | Balance questions with assumptions |
| expert | Precise requirements | Be precise, minimal explanation |
| terse | Minimal words | Just generate, no explanation |
| verbose | Over-explains | Explain every decision in detail |

## Example: Running All Scenarios

User asks: "Run all scenarios with beginner persona"

You should:
1. List scenarios in `tests/domains/aws/scenarios/`
2. For each, read `prompts/beginner.md` and generate a package
3. Validate with lint/build/cfn-lint
4. Report results

## Scoring Rubric

| Dimension | 3 points | 2 points | 1 point | 0 points |
|-----------|----------|----------|---------|----------|
| Completeness | All resources | Most resources | Some | None |
| Lint Quality | Pass first try | Pass in 2 cycles | Pass in 3+ | Never pass |
| Code Quality | Clean + no cfn-lint warnings | No errors | Has errors | Broken |
| Output Validity | cfn-lint clean | Warnings only | Errors | No output |
| Question Efficiency | 0-2 questions | 3-4 questions | 5+ questions | - |

**Pass threshold: 10/15**
