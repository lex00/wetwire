# Developer Guide

Comprehensive guide for developers working on wetwire-aws.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Code Generation](#code-generation)
- [Contributing](#contributing)

---

## Development Setup

### Prerequisites

- **Python 3.11+** (required)
- **uv** (recommended package manager)
- **git** (version control)

### Clone and Setup

```bash
# Clone repository
git clone https://github.com/lex00/wetwire.git
cd wetwire/python/packages/wetwire-aws

# Install dependencies (creates .venv automatically)
uv sync

# Install codegen dependencies
uv sync --extra codegen

# Verify installation
uv run pytest tests/ -v
```

---

## Project Structure

```
wetwire-aws/
├── src/wetwire_aws/           # Source code
│   ├── __init__.py            # Package entry point
│   ├── base.py                # CloudFormationResource base class
│   ├── decorator.py           # @wetwire_aws decorator
│   ├── template.py            # CloudFormationTemplate class
│   ├── cli.py                 # CLI commands
│   ├── intrinsics/            # Intrinsic functions
│   │   ├── functions.py       # Ref, GetAtt, Sub, Join, etc.
│   │   ├── pseudo.py          # AWS pseudo-parameters
│   │   └── refs.py            # ref(), get_att(), graph-refs integration
│   └── resources/             # Generated AWS resources (263 services)
│       ├── s3/__init__.py     # S3 resources
│       ├── ec2/__init__.py    # EC2 resources
│       ├── lambda_/__init__.py # Lambda resources
│       └── ...                # All other AWS services
├── codegen/                   # Code generation tools
│   ├── config.py              # Version configuration
│   ├── fetch.py               # Download CloudFormation spec
│   ├── parse.py               # Parse spec into intermediate format
│   ├── generate.py            # Generate Python classes
│   ├── extract_enums.py       # Extract botocore enums
│   └── intermediate.py        # Intermediate representation
├── specs/                     # CloudFormation spec (committed)
├── tests/                     # Test suite
├── docs/                      # Documentation
├── scripts/                   # Automation scripts
└── pyproject.toml             # Package configuration
```

---

## Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ --cov=wetwire_aws --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_template.py -v

# Run specific test
uv run pytest tests/test_template.py::test_from_registry -v
```

---

## Code Generation

The generator produces Python modules for each AWS service by combining two data sources:

1. **CloudFormation Resource Specification** - Defines resource types, properties, and structure
2. **Botocore Service Models** - Provides enum values for type-safe constants

### Pipeline Stages

```
┌─────────────────────────────────────────────────────────────┐
│                     Code Generation Pipeline                  │
│                                                               │
│  ┌─────────┐    ┌─────────┐    ┌──────────┐    ┌──────────┐  │
│  │  FETCH  │ ─▶ │  PARSE  │ ─▶ │ GENERATE │ ─▶ │  OUTPUT  │  │
│  └─────────┘    └─────────┘    └──────────┘    └──────────┘  │
│                                                               │
│  Download       Parse into     Generate        Write Python  │
│  CF spec &      intermediate   Python code    to resources/  │
│  botocore       format                                        │
└─────────────────────────────────────────────────────────────┘
```

### Running the Pipeline

```bash
# Full regeneration (from package root)
./scripts/regenerate.sh

# Or run stages individually (from package root)
python -m codegen.fetch
python -m codegen.parse
python -m codegen.generate

# Regenerate specific service
python -m codegen.generate --service s3
```

### CloudFormation Spec

**Source URL:** `https://d1uauaxba7bl26.cloudfront.net/latest/gzip/CloudFormationResourceSpecification.json`

The spec defines:
- **Resource Types**: `AWS::S3::Bucket`, `AWS::Lambda::Function`, etc.
- **Property Types**: Nested structures like `BucketEncryption`, `KeySchema`
- **Attributes**: Values retrievable via `!GetAtt` (e.g., `Arn`, `DomainName`)

### Botocore Enums

**Source:** Installed `botocore` package

The generator extracts enum values from botocore service models:

```python
# From botocore dynamodb model
class KeyType:
    HASH = "HASH"
    RANGE = "RANGE"

class AttributeType:
    S = "S"
    N = "N"
    B = "B"
```

This provides type-safe constants instead of magic strings.

### Generated Output

For each service, the generator produces:

```python
"""
AWS S3 CloudFormation resources.

Auto-generated from CloudFormation spec version X.X.X
Generator version: 1.0.0
Generated: 2025-12-26

DO NOT EDIT MANUALLY
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Union

from wetwire_aws.base import CloudFormationResource, PropertyType
from wetwire_aws.intrinsics.functions import Ref, GetAtt, Sub

# Enum classes from botocore
class ServerSideEncryption:
    AES256 = "AES256"
    AWS_KMS = "aws:kms"

# Property type dataclasses
@dataclass
class BucketEncryption(PropertyType):
    server_side_encryption_configuration: list[dict[str, Any]]

# Resource dataclasses
@dataclass
class Bucket(CloudFormationResource):
    _resource_type = "AWS::S3::Bucket"

    bucket_name: Optional[str] = None
    bucket_encryption: Optional[BucketEncryption] = None
    # ... more properties
```

---

## Contributing

### Code Style

- **Formatting**: Use `black` (line length 100)
- **Linting**: Use `ruff`
- **Type Hints**: Required for all public APIs

```bash
# Format code
uv run black src/ tests/

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy src/wetwire_aws/
```

### Commit Messages

Follow conventional commits:

```
feat: Add support for EC2 resources
fix: Correct S3 bucket serialization
docs: Update installation instructions
test: Add tests for graph-refs integration
chore: Update dependencies
```

### Pull Request Process

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes with tests
3. Run tests: `uv run pytest tests/`
4. Commit with clear messages
5. Push and open Pull Request
6. Address review comments

---

## See Also

- [Quick Start](QUICK_START.md) - Getting started
- [CLI Reference](CLI.md) - CLI commands
- [Internals](INTERNALS.md) - Architecture details
- [Versioning](VERSIONING.md) - Version management
