# Versioning

This document explains the versioning system for wetwire-aws.

## Version Types

The project maintains **three independent version streams**:

| Version | Format | Purpose |
|---------|--------|---------|
| **Package Version** | Semantic (X.Y.Z) | PyPI releases, API changes |
| **CloudFormation Spec** | AWS version string | Track AWS spec updates |
| **Generator Version** | Semantic (X.Y.Z) | Track code generator changes |

### Package Version

The main version for PyPI releases. Follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (X): Breaking API changes
- **MINOR** (Y): New features, backwards compatible
- **PATCH** (Z): Bug fixes, backwards compatible

**Location:** `pyproject.toml`

### CloudFormation Spec Version

Tracks which AWS CloudFormation spec was used to generate resource classes.

**Source:** Extracted from the `Last-Modified` HTTP header when fetching the spec.

**Format:** `YYYY.MM.DD` (e.g., `2025.12.11`)

**Location:** Stored in `specs/manifest.json` after fetch.

### Generator Version

Tracks changes to the code generation logic itself.

**Location:** `codegen/config.py`

```python
GENERATOR_VERSION = "1.0.0"
```

---

## Generated Code Metadata

All generated resource files include version metadata in their headers:

```python
"""
AWS S3 CloudFormation resources.

Auto-generated from CloudFormation spec version 2025.12.11
Generator version: 1.0.0
Generated: 2025-12-26 10:30:00

DO NOT EDIT MANUALLY
"""
```

---

## Bumping the Package Version

When releasing a new version:

1. Update `pyproject.toml`:
   ```toml
   [project]
   version = "0.2.0"
   ```

2. Update version in `src/wetwire_aws/__init__.py`:
   ```python
   __version__ = "0.2.0"
   ```

3. Run tests:
   ```bash
   uv run pytest tests/
   ```

4. Commit and tag:
   ```bash
   git commit -am "Bump version to 0.2.0"
   git tag wetwire-aws-v0.2.0
   git push && git push --tags
   ```

   Note: The tag format `wetwire-aws-vX.Y.Z` triggers the release workflow.

---

## Bumping the CloudFormation Spec

When AWS releases a new CloudFormation spec:

1. Run the fetch stage (captures `Last-Modified` header as version):
   ```bash
   python -m codegen.fetch --force
   ```

2. Run the full regeneration:
   ```bash
   ./scripts/regenerate.sh
   ```

3. Run tests to verify generated code:
   ```bash
   uv run pytest tests/
   ```

4. Commit with spec date in message:
   ```bash
   git commit -am "Update to CloudFormation spec YYYY.MM.DD"
   ```

5. Bump the package version (usually minor bump)

---

## Bumping the Generator Version

When changing the code generator logic:

1. Update `GENERATOR_VERSION` in `codegen/config.py`:
   ```python
   GENERATOR_VERSION = "1.1.0"
   ```

2. Regenerate all resources:
   ```bash
   ./scripts/regenerate.sh
   ```

3. Run tests:
   ```bash
   uv run pytest tests/
   ```

4. Commit:
   ```bash
   git commit -am "Generator v1.1.0: <description of changes>"
   ```

5. Bump the package version

---

## Viewing Current Versions

### From Python

```python
from wetwire_aws import __version__
print(__version__)  # "0.1.0"
```

### From CLI

```bash
wetwire-aws --version
```

### From Generated Files

Check the header of any generated resource file:

```bash
head -10 src/wetwire_aws/resources/s3/__init__.py
```

---

## Version Compatibility

| wetwire-aws | dataclass-dsl |
|-------------|---------------|
| 0.1.x | 0.1.x |

The packages are versioned together during early development. API stability will be established at 1.0.0.

---

## See Also

- [Developer Guide](DEVELOPERS.md) - Full development guide
- [Internals](INTERNALS.md) - Code generation details
