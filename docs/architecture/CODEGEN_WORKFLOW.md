# Code Generation Workflow

**Version:** 0.2
**Status:** Draft
**Last Updated:** 2024-12-26

> **This is the language-agnostic specification.** For implementation details, see the individual repository documentation.

## Overview

Each wetwire domain package (wetwire-aws, wetwire-gcp, etc.) generates typed resource definitions from vendor schemas. This document defines a unified three-stage workflow that all implementations must follow.

## The Three Stages

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Code Generation Pipeline                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   STAGE 1: FETCH              STAGE 2: PARSE              STAGE 3: GENERATE │
│   ─────────────────          ─────────────────           ─────────────────  │
│                                                                              │
│   Download vendor     →      Parse into unified    →     Generate typed     │
│   source materials           intermediate format         resource defs      │
│                                                                              │
│   Output: specs/             Output: specs/              Output: src/.../   │
│           raw files                  parsed.json                resources/  │
│           manifest.json                                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Stage 1: Fetch

**Purpose:** Download source materials from vendor sources.

**Requirements:**
- Idempotent (can run multiple times safely)
- Network-resilient (retries, timeouts)
- Version-tracked (records what was fetched)
- Validates fetched content

**Output:**
- Raw source files in `specs/` directory
- `specs/manifest.json` with metadata

**The `specs/` directory is gitignored** — source materials are never committed.

### Stage 2: Parse

**Purpose:** Transform vendor-specific schemas into a unified intermediate format.

**Requirements:**
- Reads from `specs/` directory
- Produces normalized schema representation
- Handles vendor-specific quirks
- Validates parsed output

**Output:**
- `specs/parsed.json` — unified intermediate representation

### Stage 3: Generate

**Purpose:** Generate typed resource definitions from the intermediate format.

**Requirements:**
- Reads from `specs/parsed.json`
- Generates well-formatted source code
- Generates type stubs/definitions for IDE support
- Code is committed to the repository

**Output:**
- Source modules in `src/<package>/resources/`

---

## Directory Structure

Each domain package follows this structure:

```
wetwire-<domain>/
├── specs/                      # .gitignore'd (except .gitkeep)
│   ├── .gitkeep               # Ensures directory exists in git
│   ├── manifest.json          # Fetch metadata (versions, dates)
│   ├── <raw-files>            # Vendor-specific source files
│   └── parsed.json            # Unified intermediate format
│
├── codegen/
│   ├── fetch                  # Stage 1 implementation
│   ├── parse                  # Stage 2 implementation
│   ├── generate               # Stage 3 implementation
│   └── templates/             # Code generation templates
│
├── scripts/
│   └── regenerate             # Run all three stages
│
└── src/<package>/
    └── resources/             # GENERATED (committed to git)
```

---

## Manifest Format

`specs/manifest.json` tracks what was fetched and generated:

```json
{
  "fetched_at": "2024-12-26T20:30:00Z",
  "domain": "aws",
  "generator_version": "1.0.0",
  "sources": [
    {
      "name": "cloudformation-spec",
      "type": "http",
      "url": "https://example.com/spec.json",
      "version": "208.0.0",
      "sha256": "abc123...",
      "fetched_at": "2024-12-26T20:30:00Z",
      "local_path": "spec.json"
    },
    {
      "name": "secondary-source",
      "type": "pip",
      "package": "some-package",
      "version": "1.34.50",
      "fetched_at": "2024-12-26T20:30:00Z",
      "note": "Used for enum extraction"
    }
  ],
  "status": "success"
}
```

---

## Generator Versioning

Each domain package tracks its **generator version** separately from the package version.

| Version | What It Tracks | When to Bump |
|---------|----------------|--------------|
| Package version | API changes, bug fixes | Any release |
| Generator version | Codegen logic changes | When regenerating produces different output |
| Source versions | Vendor schema updates | Automatically via fetch |

### When to Bump Generator Version

Bump `generator_version` when changes to codegen would produce different output:

- Template changes (different formatting, comments, structure)
- New fields extracted from source schemas
- Changed naming conventions
- Bug fixes in parsing logic

**Do NOT bump** for:
- Refactoring that produces identical output
- Changes to fetch logic only
- Documentation updates

### Version Metadata in Generated Files

Generated source files include version metadata in their headers:

```
Generated:
  Source: <source-name> <version>
  Generator: <generator-version>
  Date: <timestamp>
```

---

## Intermediate Format

The parsed intermediate format normalizes vendor schemas:

```json
{
  "schema_version": "1.0",
  "domain": "aws",
  "generated_at": "2024-12-26T20:35:00Z",
  "resources": [
    {
      "name": "Bucket",
      "service": "s3",
      "full_type": "AWS::S3::Bucket",
      "documentation": "Creates an S3 bucket",
      "properties": [
        {
          "name": "bucket_name",
          "original_name": "BucketName",
          "type": "string",
          "required": false,
          "documentation": "The name of the bucket"
        }
      ],
      "attributes": [
        {
          "name": "Arn",
          "type": "string",
          "documentation": "The ARN of the bucket"
        }
      ]
    }
  ],
  "enums": [
    {
      "name": "VersioningStatus",
      "service": "s3",
      "values": ["Enabled", "Suspended"]
    }
  ],
  "nested_types": [
    {
      "name": "VersioningConfiguration",
      "service": "s3",
      "properties": [...]
    }
  ]
}
```

---

## Platform-Specific Sources

Each platform has different source locations and formats:

| Platform | Sources | Format |
|----------|---------|--------|
| **AWS** | CF spec + botocore | JSON + pip package |
| **GCP** | Config Connector CRDs | YAML (GitHub) |
| **Azure** | ARM schemas | JSON (GitHub) |
| **Kubernetes** | OpenAPI spec | JSON (GitHub) |
| **GitHub Actions** | Workflow schema + action.yml | JSON + YAML (multiple sources) |

---

## Fetch Methods

### HTTP Fetch

Download a file via HTTP/HTTPS. Supports:
- Automatic decompression (gzip)
- SHA256 verification
- Retry with backoff

### Git Sparse Checkout

Clone specific paths from a git repository. Supports:
- Sparse checkout (only fetch needed paths)
- Shallow clone (single commit)
- Tag/branch pinning

### Package Manager Info

Record version information for installed packages (pip, npm, cargo, etc.). Does not download — assumes package is installed.

---

## Validation Requirements

### Stage 1 (Fetch) Validation
- HTTP responses return 200
- Files are non-empty
- JSON/YAML files parse successfully
- SHA256 matches expected (if pinned)

### Stage 2 (Parse) Validation
- All required fields present
- Type references resolve
- No duplicate resource names
- Enums have at least one value

### Stage 3 (Generate) Validation
- Generated code is syntactically valid
- Imports resolve correctly
- Type definitions are valid

---

## Caching and Freshness

### Skip Fetch If Fresh

Implementations should check manifest age before fetching:

```
if manifest exists AND age < max_age:
    skip fetch
else:
    run fetch
```

Default max age: 24 hours.

### Force Refresh

All implementations must support a `--force` flag to bypass freshness check.

---

## CI/CD Integration

### Weekly Regeneration Workflow

```
1. Checkout repository
2. Install dependencies
3. Run fetch (with --force)
4. Run parse
5. Run generate
6. Check for changes (git diff)
7. If changes: create PR with title "chore(<domain>): regenerate resources"
```

This ensures resources stay current with upstream schema changes.

---

## Gitignore Pattern

Each domain package's `.gitignore`:

```gitignore
# Fetched specs (never commit)
specs/*
!specs/.gitkeep
```

---

## Implementation Requirements

Each language implementation MUST provide:

1. **Fetch Stage**
   - HTTP fetcher with retry logic
   - Git sparse checkout support
   - Package version detection
   - Manifest writer

2. **Parse Stage**
   - Vendor-specific schema parser
   - Intermediate format generator
   - Validation

3. **Generate Stage**
   - Template engine integration
   - Code formatter integration
   - Type stub generation

4. **CLI/Scripts**
   - `fetch` command
   - `parse` command
   - `generate` command
   - `regenerate` command (all three)

---

## Summary

| Stage | Input | Output | Committed? |
|-------|-------|--------|------------|
| **Fetch** | Vendor URLs/repos | `specs/*` + `manifest.json` | No |
| **Parse** | `specs/*` | `specs/parsed.json` | No |
| **Generate** | `specs/parsed.json` | `src/.../resources/` | Yes |

This workflow ensures:
1. **Reproducibility** — Manifest tracks exact versions
2. **Separation** — Vendor files never committed
3. **Flexibility** — Each platform implements its own fetch logic
4. **Consistency** — Common intermediate format
5. **Automation** — CI can regenerate weekly

---

## Related Documents

- [ARCHITECTURE.md](ARCHITECTURE.md) — Overall system architecture
