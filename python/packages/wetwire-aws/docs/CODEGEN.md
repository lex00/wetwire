# Python Code Generation Implementation

**Version:** 0.1
**Status:** Draft
**Last Updated:** 2024-12-26

> **This document extends the language-agnostic specification.**
> See: [docs/architecture/CODEGEN_WORKFLOW.md](../../docs/architecture/CODEGEN_WORKFLOW.md)

## Overview

This document describes the Python-specific implementation of the wetwire code generation workflow.

---

## Directory Structure

```
wetwire-aws/
├── specs/                      # .gitignore'd (except .gitkeep)
│   ├── .gitkeep
│   ├── manifest.json
│   ├── CloudFormationResourceSpecification.json
│   └── parsed.json
│
├── codegen/
│   ├── __init__.py
│   ├── fetch.py               # Stage 1: python -m codegen.fetch
│   ├── parse.py               # Stage 2: python -m codegen.parse
│   ├── generate.py            # Stage 3: python -m codegen.generate
│   ├── intermediate.py        # Intermediate format dataclasses
│   ├── config.py              # Generator version, URLs, etc.
│   └── extract_enums.py       # Extract enums from botocore
│
├── scripts/
│   ├── fetch.sh               # Wrapper: python -m codegen.fetch
│   ├── parse.sh               # Wrapper: python -m codegen.parse
│   ├── generate.sh            # Wrapper: python -m codegen.generate
│   └── regenerate.sh          # Run all three stages
│
└── src/wetwire_aws/
    └── resources/             # GENERATED (.gitignore'd, created at build)
        ├── __init__.py
        ├── s3/
        │   ├── __init__.py    # Resources and enums
        │   ├── bucket.py      # PropertyTypes for Bucket
        │   └── ...
        ├── dynamodb/
        │   ├── __init__.py
        │   ├── table.py       # PropertyTypes for Table
        │   └── ...
        ├── lambda_/           # Underscore to avoid keyword
        ├── iam/
        └── ...
```

---

## CLI Commands

```bash
# Stage 1: Fetch source materials
python -m wetwire_aws.codegen.fetch
python -m wetwire_aws.codegen.fetch --force  # Bypass freshness check

# Stage 2: Parse into intermediate format
python -m wetwire_aws.codegen.parse
python -m wetwire_aws.codegen.parse --validate  # Extra validation

# Stage 3: Generate Python code
python -m wetwire_aws.codegen.generate
python -m wetwire_aws.codegen.generate --format  # Run black
python -m wetwire_aws.codegen.generate --dry-run  # Preview only

# All stages
./scripts/regenerate.sh
```

---

## AWS-Specific Sources

### CloudFormation Specification

```python
# codegen/config.py

SOURCES = [
    {
        "name": "cloudformation-spec",
        "type": "http",
        "url": "https://d1uauaxba7bl26.cloudfront.net/latest/gzip/CloudFormationResourceSpecification.json",
        "extract_version": lambda data: data.get("ResourceSpecificationVersion"),
    },
    {
        "name": "botocore",
        "type": "pip",
        "package": "botocore",
        # Version comes from installed package
    },
]

GENERATOR_VERSION = "1.0.0"
```

### Why Two Sources?

- **CF Spec**: Resource types, property structures, required fields, GetAtt attributes
- **botocore**: Enum values (e.g., `BillingMode = "PROVISIONED" | "PAY_PER_REQUEST"`)

The CF spec doesn't include enum values, so we extract them from botocore service models.

---

## Fetch Implementation

```python
# codegen/fetch.py

import gzip
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

import requests


def fetch_http(source: dict, specs_dir: Path) -> dict:
    """Fetch a file via HTTP."""
    url = source["url"]
    filename = source.get("filename", url.split("/")[-1])
    local_path = specs_dir / filename

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    content = response.content
    if "gzip" in url or url.endswith(".gz"):
        content = gzip.decompress(content)

    local_path.write_bytes(content)

    # Extract version if extractor provided
    version = None
    if "extract_version" in source:
        data = json.loads(content)
        version = source["extract_version"](data)

    return {
        "name": source["name"],
        "type": "http",
        "url": url,
        "version": version,
        "sha256": hashlib.sha256(content).hexdigest(),
        "local_path": filename,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }


def fetch_pip_info(source: dict) -> dict:
    """Get version info for an installed pip package."""
    package = source["package"]

    result = subprocess.run(
        ["pip", "show", package],
        capture_output=True,
        text=True,
        check=True,
    )

    version = None
    for line in result.stdout.splitlines():
        if line.startswith("Version:"):
            version = line.split(":", 1)[1].strip()
            break

    return {
        "name": source["name"],
        "type": "pip",
        "package": package,
        "version": version,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }


def fetch_git_sparse(source: dict, specs_dir: Path) -> dict:
    """Fetch specific paths from a git repo using sparse checkout."""
    import shutil

    repo_dir = specs_dir / source["name"]

    if repo_dir.exists():
        shutil.rmtree(repo_dir)

    subprocess.run(
        [
            "git", "clone",
            "--depth", "1",
            "--filter=blob:none",
            "--sparse",
            source["repo"],
            str(repo_dir),
        ],
        check=True,
    )

    subprocess.run(
        ["git", "-C", str(repo_dir), "sparse-checkout", "set", *source["sparse_paths"]],
        check=True,
    )

    # Get commit hash
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    commit = result.stdout.strip()

    return {
        "name": source["name"],
        "type": "git",
        "repo": source["repo"],
        "ref": source.get("ref", "HEAD"),
        "commit": commit,
        "sparse_paths": source["sparse_paths"],
        "local_path": repo_dir.name,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }
```

---

## Intermediate Format Dataclasses

```python
# codegen/intermediate.py

from dataclasses import dataclass, field


@dataclass
class PropertyDef:
    name: str
    original_name: str
    type: str
    required: bool = False
    documentation: str = ""
    nested_type: str | None = None
    enum_type: str | None = None
    constraints: dict = field(default_factory=dict)


@dataclass
class AttributeDef:
    name: str
    type: str
    documentation: str = ""


@dataclass
class ResourceDef:
    name: str
    service: str
    full_type: str
    documentation: str = ""
    properties: list[PropertyDef] = field(default_factory=list)
    attributes: list[AttributeDef] = field(default_factory=list)


@dataclass
class EnumDef:
    name: str
    service: str
    values: list[str] = field(default_factory=list)
    documentation: str = ""


@dataclass
class NestedTypeDef:
    name: str
    service: str
    properties: list[PropertyDef] = field(default_factory=list)


@dataclass
class IntermediateSchema:
    schema_version: str
    domain: str
    generated_at: str
    resources: list[ResourceDef] = field(default_factory=list)
    enums: list[EnumDef] = field(default_factory=list)
    nested_types: list[NestedTypeDef] = field(default_factory=list)
```

---

## Generated Code Structure

The generator produces Python code directly (no templates). Each service gets:

1. **`__init__.py`** - Resources and enum constants
2. **`{resource}.py`** - PropertyTypes for each resource

### Example: S3 Service

**s3/__init__.py:**
```python
"""AWS S3 CloudFormation resources."""

from wetwire_aws.base import CloudFormationResource, PropertyType, Tag
from . import bucket as _bucket  # Submodule for PropertyTypes

# Enum constants
class ServerSideEncryption:
    AES256 = "AES256"
    AWS_KMS = "aws:kms"

# Resources reference PropertyTypes via submodule
@dataclass
class Bucket(CloudFormationResource):
    _resource_type: ClassVar[str] = "AWS::S3::Bucket"
    bucket_name: str | None = None
    bucket_encryption: _bucket.BucketEncryption | None = None
```

**s3/bucket.py:**
```python
"""PropertyTypes for AWS::S3::Bucket."""

from wetwire_aws.base import PropertyType

@dataclass
class BucketEncryption(PropertyType):
    server_side_encryption_configuration: list[ServerSideEncryptionRule] = field(default_factory=list)
```

---

## Generated File Header

All generated Python files include this header:

```python
"""
AWS S3 CloudFormation resources.

Generated:
  Source: CloudFormation Spec 228.0.0
  Generator: 1.0.0
  Date: 2025-12-27T22:26:01Z

DO NOT EDIT - This file is generated by wetwire-aws codegen.
To regenerate: python -m wetwire_aws.codegen.generate
"""
```

---

## Dependencies

```toml
# pyproject.toml for wetwire-aws

[project]
dependencies = [
    "wetwire>=0.1.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
codegen = [
    "requests>=2.28",
    "jinja2>=3.1",
    "black>=23.12",
    "botocore>=1.34",  # For enum extraction
]
```

---

## Validation

### Syntax Validation

```python
import ast

def validate_syntax(path: Path) -> bool:
    """Check if generated Python is syntactically valid."""
    try:
        ast.parse(path.read_text())
        return True
    except SyntaxError as e:
        print(f"Syntax error in {path}: {e}")
        return False
```

### Type Checking

```bash
# After generation, run type checker
mypy src/wetwire_aws/resources/ --strict
pyright src/wetwire_aws/resources/
```

---

## CI/CD Workflow

```yaml
# .github/workflows/regenerate-aws.yml
name: Regenerate AWS Resources

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:

jobs:
  regenerate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -e "python/packages/wetwire-aws[codegen]"

      - name: Regenerate
        run: |
          cd python/packages/wetwire-aws
          python -m codegen.fetch --force
          python -m codegen.parse
          python -m codegen.generate --format

      - name: Validate
        run: |
          cd python/packages/wetwire-aws
          python -c "import wetwire_aws.resources"
          mypy src/wetwire_aws/resources/ --strict

      - name: Check for changes
        id: diff
        run: |
          git diff --exit-code || echo "has_changes=true" >> $GITHUB_OUTPUT

      - name: Create PR
        if: steps.diff.outputs.has_changes == 'true'
        uses: peter-evans/create-pull-request@v5
        with:
          title: "chore(aws): regenerate resources"
          body: |
            Automated regeneration from upstream CloudFormation spec changes.

            See manifest.json for version details.
          branch: regenerate-aws
```

---

## Related Documents

- [CODEGEN_WORKFLOW.md](../../docs/architecture/CODEGEN_WORKFLOW.md) — Language-agnostic specification
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) — Overall Python implementation plan
- [CF_DATACLASSES.md](CF_DATACLASSES.md) — CloudFormation-specific patterns
