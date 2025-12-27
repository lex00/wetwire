# Python Agent Workflow Implementation

**Version:** 0.1
**Status:** Draft
**Last Updated:** 2024-12-26

> **This document extends the language-agnostic specification.**
> See: [docs/architecture/AGENT_WORKFLOW.md](../../docs/architecture/AGENT_WORKFLOW.md)

## Overview

This document describes the Python-specific implementation of the wetwire agent workflow.

---

## CLI Commands

### Production Use

```bash
# Interactive session with human as Developer
wetwire design --domain aws

# Human provides: "I need a VPC with private subnets and a database"
# Runner asks questions, builds package, runs lint cycles
# Human answers questions about intent
# Output: Complete wetwire package + RESULTS.md
```

### Testing Use

```bash
# Automated session with Claude as Developer
wetwire test --domain aws --persona expert --prompt "Private VPC with RDS"

# Both Developer and Runner are Claude instances
# Persona shapes Developer's behavior
# Output: Package + RESULTS.md + metrics
```

### Batch Testing

```bash
# Run all prompts in a suite with all personas
wetwire test --domain aws --suite medium --all-personas

# Run specific prompt with specific persona
wetwire test --domain aws --persona beginner --prompt "S3 bucket for logs"
```

---

## Directory Structure

```
wetwire-aws/
└── tests/
    └── agent/
        ├── prompts/
        │   ├── simple.yaml
        │   ├── medium.yaml
        │   ├── complex.yaml
        │   └── adversarial.yaml
        ├── baselines/
        │   └── (expected outputs for regression)
        └── results/
            └── (generated RESULTS.md files)
```

---

## Prompt File Format

```yaml
# prompts/medium.yaml
prompts:
  - id: vpc-public-private
    prompt: "VPC with public and private subnets"
    expected_resources:
      - AWS::EC2::VPC
      - AWS::EC2::Subnet
      - AWS::EC2::InternetGateway
      - AWS::EC2::NatGateway
    max_cycles: 2
    max_questions: 3

  - id: lambda-s3-trigger
    prompt: "Lambda triggered by S3 uploads"
    expected_resources:
      - AWS::Lambda::Function
      - AWS::IAM::Role
      - AWS::S3::Bucket
    max_cycles: 2
    max_questions: 2
```

---

## Domain-Specific Prompts

### AWS (wetwire-aws)

#### Simple
| Prompt | Expected Resources |
|--------|-------------------|
| "S3 bucket for static website" | Bucket, BucketPolicy |
| "SNS topic with email subscription" | Topic, Subscription |
| "DynamoDB table for sessions" | Table |

#### Medium
| Prompt | Expected Resources |
|--------|-------------------|
| "VPC with public and private subnets" | VPC, Subnets, IGW, NAT, RouteTables |
| "Lambda triggered by S3 uploads" | Lambda, Role, Bucket, Event |
| "RDS PostgreSQL in private subnet" | RDS, SubnetGroup, SecurityGroup |

#### Complex
| Prompt | Expected Resources |
|--------|-------------------|
| "Autoscaled EC2 in private VPC with SSH" | VPC, Subnets, NAT, ASG, SG, IAM |
| "ECS Fargate with ALB and RDS" | Cluster, Service, TaskDef, ALB, RDS |
| "Serverless API with Lambda and DynamoDB" | Lambda, APIGW, DynamoDB, IAM |

---

## Component Locations

| Component | Location |
|-----------|----------|
| Personas | `docs/personas/*.md` |
| Orchestrator | `python/packages/wetwire/src/wetwire/orchestrator.py` |
| RESULTS.md template | `python/packages/wetwire/src/wetwire/templates/` |
| Scoring rubric | `python/packages/wetwire/src/wetwire/scoring.py` |
| AWS Prompt library | `python/packages/wetwire-aws/tests/agent/prompts/` |
| AWS CLI tools | `python/packages/wetwire-aws/src/wetwire_aws/cli/` |

---

## Output Structure

```
output/
├── ec2_private_vpc/           # Generated package
│   ├── ec2_private_vpc/
│   │   ├── __init__.py
│   │   ├── network.py
│   │   ├── compute.py
│   │   └── security.py
│   ├── pyproject.toml
│   └── RESULTS.md
└── logs/
    └── ec2_private_vpc/
        ├── session.json       # Metadata
        ├── conversation.md    # Human-readable transcript
        ├── developer.jsonl    # Developer messages
        └── runner.jsonl       # Runner messages
```

---

## Python Implementation Notes

### Orchestrator

Uses the Anthropic Python SDK to manage conversations:

```python
from anthropic import Anthropic

class Orchestrator:
    def __init__(self, domain: str, persona: str | None = None):
        self.client = Anthropic()
        self.domain = domain
        self.persona = persona

    def run_session(self, prompt: str) -> SessionResult:
        # Initialize Developer and Runner
        # Coordinate message passing
        # Enforce cycle limits
        # Return results
        ...
```

### Persona Loading

Personas are loaded from markdown files in `docs/personas/`:

```python
from pathlib import Path

def load_persona(name: str) -> str:
    """Load persona system prompt from markdown file."""
    path = Path(__file__).parent.parent.parent.parent / "docs" / "personas" / f"{name}.md"
    return path.read_text()
```

### Scoring

```python
from dataclasses import dataclass

@dataclass
class SessionScore:
    completeness: int  # 0-3
    lint_quality: int  # 0-3
    code_quality: int  # 0-3
    output_validity: int  # 0-3
    question_efficiency: int  # 0-3

    @property
    def total(self) -> int:
        return (
            self.completeness +
            self.lint_quality +
            self.code_quality +
            self.output_validity +
            self.question_efficiency
        )
```

---

## Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "anthropic>=0.18",
    "pyyaml>=6.0",
    "rich>=13.0",  # For CLI output
]
```

---

## Related Documents

- [AGENT_WORKFLOW.md](../../docs/architecture/AGENT_WORKFLOW.md) — Language-agnostic specification
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) — Overall Python implementation plan
