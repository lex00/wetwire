# /run-scenario

Run a wetwire-agent scenario by generating a package and validating it.

## Usage

```
/run-scenario <path> [--persona <name>]
/run-scenario tests/domains/aws/scenarios/s3_log_bucket
/run-scenario tests/domains/aws/scenarios/s3_log_bucket --persona expert
/run-scenario all --persona beginner
```

## Instructions

When this skill is invoked:

### 1. Parse Arguments

- `<path>`: Path to scenario directory, or "all" to run all scenarios
- `--persona`: One of beginner, intermediate, expert, terse, verbose (default: beginner)

### 2. For Each Scenario

#### A. Read the persona-specific prompt
```bash
cat <scenario>/prompts/<persona>.md
```

Each persona has a different prompt style:
- **beginner**: Vague, uncertain, defers to suggestions
- **intermediate**: Some knowledge, asks clarifying questions
- **expert**: Precise requirements, technical terminology
- **terse**: Minimal words, expects you to figure it out
- **verbose**: Over-explains with context and concerns

#### B. Generate a package

Create a wetwire-aws package that fulfills the prompt:

```python
# <scenario>/generated/__init__.py
from wetwire_aws.loader import setup_resources
setup_resources(__file__, __name__, globals())
```

```python
# <scenario>/generated/<resource>.py
from . import *

class <ResourceName>:
    resource: <service>.<Resource>
    # Add appropriate properties based on prompt
```

**Module path patterns:**
- **Resources**: `s3.Bucket`, `ec2.Instance`, `lambda_.Function`
- **PropertyTypes**: `s3.bucket.ServerSideEncryptionByDefault`, `s3.bucket.PublicAccessBlockConfiguration`
- **Enums**: `s3.ServerSideEncryption.AES256`, `lambda_.Runtime.PYTHON3_12`

**Example S3 bucket with encryption and public access block:**
```python
from . import *

class MyEncryptionDefault:
    resource: s3.bucket.ServerSideEncryptionByDefault
    sse_algorithm = s3.ServerSideEncryption.AES256

class MyEncryptionRule:
    resource: s3.bucket.ServerSideEncryptionRule
    server_side_encryption_by_default = MyEncryptionDefault

class MyEncryption:
    resource: s3.bucket.BucketEncryption
    server_side_encryption_configuration = [MyEncryptionRule]

class MyPublicAccessBlock:
    resource: s3.bucket.PublicAccessBlockConfiguration
    block_public_acls = True
    block_public_policy = True
    ignore_public_acls = True
    restrict_public_buckets = True

class MyBucket:
    resource: s3.Bucket
    bucket_encryption = MyEncryption
    public_access_block_configuration = MyPublicAccessBlock
```

**Runner behavior by persona:**
- beginner: Make safe defaults, explain choices, be helpful
- intermediate: Balance assumptions with clarifying questions
- expert: Be precise, assume knowledge, minimal explanation
- terse: Just generate, no explanation needed
- verbose: Explain every decision in detail

#### C. Validate

```bash
# Lint the generated package
uv run wetwire-aws lint <scenario>/generated/

# Build CloudFormation template
PYTHONPATH=<scenario> uv run wetwire-aws build -m generated -f yaml > <scenario>/results/<persona>/template.yaml

# Run cfn-lint
uv run cfn-lint <scenario>/results/<persona>/template.yaml -f json
```

#### D. Save Results

Save to `<scenario>/results/<persona>/`:
- `template.yaml` - CloudFormation output
- `results.md` - Full report
- `score.json` - Scoring breakdown
- `generated/` - Your generated code (when acting as Runner)

Create `results.md`:

```markdown
# Package Generation Results

**Prompt:** "<prompt>"
**Persona:** <persona>
**Date:** <date>

## wetwire-aws Lint
**Status:** PASS/FAIL
**Issues:** <count>

## cfn-lint Validation
**Status:** PASS/FAIL
**Errors:** <count>
**Warnings:** <count>

## Score Breakdown
| Dimension | Score | Max |
|-----------|-------|-----|
| Completeness | X | 3 |
| Lint Quality | X | 3 |
| Code Quality | X | 3 |
| Output Validity | X | 3 |
| Question Efficiency | X | 3 |

**Total: X/15**
```

### 3. Summary

After all scenarios, print a summary table:

```
Persona         Score      Lint     cfn-lint   Status
------------------------------------------------------------
beginner        15/15      ✓        ✓          PASS
```

## Scoring

| Dimension | 3 | 2 | 1 | 0 |
|-----------|---|---|---|---|
| Completeness | All resources created | Most | Some | None |
| Lint Quality | Pass first try | 2 cycles | 3+ cycles | Never |
| Code Quality | No cfn-lint issues | Warnings only | Errors | Broken |
| Output Validity | Clean template | Warnings | Errors | No output |
| Question Efficiency | 0-2 questions | 3-4 | 5+ | - |

**Pass: >= 10/15**
