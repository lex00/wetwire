# /run-scenario

Run a wetwire-agent scenario by generating a package and validating it.

## Usage

```
/run-scenario <path> [--persona <name>]
/run-scenario testdata/scenarios/s3_log_bucket
/run-scenario testdata/scenarios/s3_log_bucket --persona expert
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

Create a wetwire-aws Go package that fulfills the prompt:

```go
// <scenario>/generated/main.go
package main

import (
    "github.com/lex00/wetwire/go/wetwire-aws/resources/s3"
    // other imports as needed
)

var MyBucket = s3.Bucket{
    BucketName: "my-bucket",
    // Add appropriate properties based on prompt
}
```

**Resource patterns:**
- **Resources**: `s3.Bucket`, `ec2.Instance`, `lambda.Function`
- **PropertyTypes**: `s3.BucketEncryption`, `s3.PublicAccessBlockConfiguration`
- **References**: `MyRole.Arn` (attribute reference to another resource)

**Example S3 bucket with encryption and public access block:**
```go
package main

import (
    "github.com/lex00/wetwire/go/wetwire-aws/resources/s3"
)

var MyEncryption = s3.BucketEncryption{
    ServerSideEncryptionConfiguration: []s3.ServerSideEncryptionRule{
        {
            ServerSideEncryptionByDefault: &s3.ServerSideEncryptionByDefault{
                SSEAlgorithm: "AES256",
            },
        },
    },
}

var MyPublicAccessBlock = s3.PublicAccessBlockConfiguration{
    BlockPublicAcls:       true,
    BlockPublicPolicy:     true,
    IgnorePublicAcls:      true,
    RestrictPublicBuckets: true,
}

var MyBucket = s3.Bucket{
    BucketEncryption:                  &MyEncryption,
    PublicAccessBlockConfiguration:    &MyPublicAccessBlock,
}
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
wetwire-aws lint <scenario>/generated/

# Build CloudFormation template
wetwire-aws build <scenario>/generated/ -f yaml > <scenario>/results/<persona>/template.yaml

# Run cfn-lint (currently Python, will be cfn-lint-go)
cfn-lint <scenario>/results/<persona>/template.yaml -f json
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

## CLI Commands

```bash
# Validate existing expected packages (no AI needed)
wetwire-agent validate-scenarios testdata/scenarios

# Run single scenario validation
wetwire-agent run-scenario testdata/scenarios/s3_log_bucket --save-results

# Run with AI generation
wetwire-agent run-scenario testdata/scenarios/s3_log_bucket --generate --persona beginner

# Run all personas
wetwire-agent run-scenario testdata/scenarios/s3_log_bucket --persona all --save-results

# Interactive design session
wetwire-agent design "I need a bucket for logs"
wetwire-agent design -o ./myapp  # modify existing package

# List available resources
wetwire-agent list personas
wetwire-agent list domains
wetwire-agent list prompts --path testdata/scenarios
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
