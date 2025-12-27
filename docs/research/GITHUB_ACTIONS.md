# Wetwire GitHub Actions Feasibility Study

**Status**: Draft
**Purpose**: Evaluate feasibility of `wetwire-actions` following the same declarative wrapper pattern.
**Scope**: **Synthesis only** - generates GitHub Actions workflow YAML; does not execute workflows.
**Recommendation**: **Proceed** - Actions have schemas, massive user base, and significant YAML pain.

---

## Executive Summary

`wetwire-actions` is a **synthesis library** - it generates GitHub Actions workflow YAML from Python dataclasses. Like other wetwire libraries, it does not perform execution.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  wetwire-actions (synthesis)                External (execution)        │
│                                                                          │
│  Action Schemas → Python Dataclasses → Workflow YAML                    │
│     (input)           (authoring)         (output)                      │
│                                                ↓                         │
│                                         GitHub Actions runner           │
│                                         (GitHub's responsibility)        │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why GitHub Actions YAML as output:**
- Native execution (push to repo, GitHub runs it)
- Massive user base (millions of repositories)
- Real pain point (complex workflows are notoriously hard to maintain)
- Schema source exists (action.yml metadata files)

**Unique value:**
- Type-safe action inputs (catch typos before push)
- Cross-job references without string copying
- Matrix builds as Python data structures
- Reusable workflow patterns as inheritance

---

## The Problem: GitHub Actions YAML Hell

### Real-World Complexity

A typical CI/CD workflow:

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']
        os: [ubuntu-latest, macos-latest]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
      - name: Run tests
        run: pytest tests/ -v
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage.xml
          fail_ci_if_error: true

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build package
        run: python -m build
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish:
    needs: build
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
```

**Pain points:**
- `actions/checkout@v4` repeated in every job
- Matrix syntax is awkward and error-prone
- `${{ matrix.python-version }}` string interpolation everywhere
- `needs: test` is a string reference (no validation)
- `secrets.CODECOV_TOKEN` — typo = silent failure
- `if:` conditions use a custom expression language
- 70+ lines for a standard Python CI workflow

### The Vision

```
from wetwire.actions import workflow, job, step
from wetwire.actions.actions import checkout, setup_python, codecov, upload_artifact

@workflow
class CI:
    on = [Push(branches=["main"]), PullRequest(branches=["main"])]

@job
class Test:
    runs_on = "ubuntu-latest"
    matrix = Matrix(
        python_version=["3.10", "3.11", "3.12"],
        os=["ubuntu-latest", "macos-latest"],
    )
    steps = [
        checkout(),
        setup_python(python_version=matrix.python_version),
        run("pip install -e '.[dev]'"),
        run("pytest tests/ -v"),
        codecov(token=secrets.CODECOV_TOKEN, files="./coverage.xml"),
    ]

@job
class Build:
    needs = Test  # Type-safe reference, not string
    runs_on = "ubuntu-latest"
    steps = [
        checkout(),
        run("python -m build"),
        upload_artifact(name="dist", path="dist/"),
    ]

@job
class Publish:
    needs = Build
    condition = Push() & TagRef("v*")  # Type-safe conditions
    runs_on = "ubuntu-latest"
    steps = [
        download_artifact(name="dist"),
        pypi_publish(password=secrets.PYPI_API_TOKEN),
    ]
```

**Improvements:**
- `checkout()` defined once, reused (or auto-included in presets)
- `needs = Test` is a class reference, not a string
- `matrix.python_version` is a typed reference
- `secrets.CODECOV_TOKEN` is validated against declared secrets
- Conditions use Python operators (`&`, `|`)
- 30 lines instead of 70+

---

## Schema Source: Action Metadata

### action.yml Files

Every GitHub Action has an `action.yml` that defines its interface:

```yaml
# actions/setup-python/action.yml
name: 'Setup Python'
description: 'Set up a specific version of Python'
inputs:
  python-version:
    description: 'Version range or exact version'
    required: false
  cache:
    description: 'Used to specify a package manager for caching'
    required: false
outputs:
  python-version:
    description: 'The installed Python version'
  cache-hit:
    description: 'Whether cache was hit'
```

This is a **schema** — we can generate type-safe Python wrappers:

```
# Generated from actions/setup-python/action.yml
@dataclass
class SetupPython(Action):
    action: ClassVar[str] = "actions/setup-python@v5"

    python_version: str | None = None
    cache: Literal["pip", "poetry", "pipenv"] | None = None

    # Outputs
    @property
    def output_python_version(self) -> StepOutput:
        return self.get_output("python-version")

    @property
    def output_cache_hit(self) -> StepOutput:
        return self.get_output("cache-hit")
```

### Workflow Schema

GitHub also publishes a JSON schema for workflow files:

```
https://json.schemastore.org/github-workflow.json
```

This defines all valid workflow syntax: triggers, job options, step properties, expressions, etc.

### Popular Actions Registry

Generate wrappers for the most popular actions:
- `actions/checkout`
- `actions/setup-python`, `setup-node`, `setup-go`, etc.
- `actions/cache`
- `actions/upload-artifact`, `download-artifact`
- `docker/build-push-action`
- `codecov/codecov-action`
- And hundreds more from the marketplace

---

## The `ref()` Pattern: Job Dependencies

### Cross-Job References

```
@job
class Test:
    runs_on = "ubuntu-latest"
    steps = [...]

@job
class Build:
    needs = Test  # Reference to Test job
    runs_on = "ubuntu-latest"
    steps = [...]

@job
class Deploy:
    needs = [Test, Build]  # Multiple dependencies
    runs_on = "ubuntu-latest"
    steps = [...]
```

Generates:
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps: [...]

  build:
    needs: test
    runs-on: ubuntu-latest
    steps: [...]

  deploy:
    needs: [test, build]
    runs-on: ubuntu-latest
    steps: [...]
```

### Job Output References

```
@job
class Build:
    runs_on = "ubuntu-latest"
    steps = [
        run("echo version=$(cat VERSION)", id="version"),
    ]
    outputs = {
        "version": steps.version.outputs.stdout,
    }

@job
class Deploy:
    needs = Build
    steps = [
        run(f"deploy --version {Build.outputs.version}"),
    ]
```

Type-safe reference to `Build.outputs.version` instead of:
```yaml
${{ needs.build.outputs.version }}
```

---

## Matrix Builds: Python Data Structures

### Current Pain

```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12']
    os: [ubuntu-latest, macos-latest]
    exclude:
      - python-version: '3.10'
        os: macos-latest
    include:
      - python-version: '3.12'
        os: ubuntu-latest
        experimental: true
```

### With Dataclasses

```
@job
class Test:
    matrix = Matrix(
        python_version=["3.10", "3.11", "3.12"],
        os=["ubuntu-latest", "macos-latest"],
    ).exclude(
        python_version="3.10", os="macos-latest"
    ).include(
        python_version="3.12", os="ubuntu-latest", experimental=True
    )

    runs_on = matrix.os
    steps = [
        setup_python(python_version=matrix.python_version),
        # ...
    ]
```

**Benefits:**
- IDE autocomplete for matrix variables
- Type checking on matrix references
- Fluent API for exclude/include
- Matrix variables are typed, not strings

---

## Conditions: Python Operators

### Current Pain

```yaml
if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')
```

Custom expression language, no IDE support, easy to typo.

### With Dataclasses

```
from wetwire.actions.conditions import Push, PullRequest, TagRef, Branch

@job
class Publish:
    condition = Push() & TagRef("v*")
    # or
    condition = event.name == "push" and ref.startswith("refs/tags/v")
```

**Condition helpers:**
```
Push()                    # github.event_name == 'push'
PullRequest()             # github.event_name == 'pull_request'
TagRef("v*")              # startsWith(github.ref, 'refs/tags/v')
Branch("main")            # github.ref == 'refs/heads/main'
Actor("dependabot[bot]")  # github.actor == 'dependabot[bot]'

# Combine with Python operators
Push() & Branch("main")                    # Push to main
PullRequest() | Push()                     # PR or push
~Actor("dependabot[bot]")                  # Not dependabot
```

---

## Secrets: Validated References

### Current Pain

```yaml
env:
  CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
```

Typo in `CODECOV_TOKEN` = silent failure (undefined secret is empty string).

### With Dataclasses

```
# Declare secrets at workflow level
@workflow
class CI:
    secrets = declare_secrets("CODECOV_TOKEN", "PYPI_API_TOKEN", "DOCKER_PASSWORD")

@job
class Test:
    steps = [
        codecov(token=secrets.CODECOV_TOKEN),  # Type-safe reference
    ]
```

**Benefits:**
- Declared secrets are validated at build time
- IDE autocomplete for secret names
- Missing secret = Python error, not silent failure

---

## Reusable Workflows: Inheritance

### Current Pain

```yaml
# .github/workflows/reusable-test.yml
on:
  workflow_call:
    inputs:
      python-version:
        required: true
        type: string

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ inputs.python-version }}
```

```yaml
# .github/workflows/ci.yml
jobs:
  call-test:
    uses: ./.github/workflows/reusable-test.yml
    with:
      python-version: '3.12'
```

Complex, spread across files, inputs are untyped.

### With Dataclasses

```
# Base reusable pattern
class PythonTestJob(Job):
    """Reusable Python test job."""
    python_version: str = "3.12"

    @property
    def steps(self):
        return [
            checkout(),
            setup_python(python_version=self.python_version),
            run("pip install -e '.[dev]'"),
            run("pytest"),
        ]

# Use via inheritance
@job
class TestPy310(PythonTestJob):
    python_version = "3.10"

@job
class TestPy311(PythonTestJob):
    python_version = "3.11"

@job
class TestPy312(PythonTestJob):
    python_version = "3.12"
```

Or with matrix:
```
@job
class Test(PythonTestJob):
    matrix = Matrix(python_version=["3.10", "3.11", "3.12"])
    python_version = matrix.python_version
```

---

## Proposed Package Structure

```
wetwire-actions/
├── specs/
│   ├── workflow-schema.json          # GitHub workflow JSON schema
│   └── actions/                      # Popular action.yml files
│       ├── checkout.yml
│       ├── setup-python.yml
│       └── ...
├── src/wetwire_actions/
│   ├── core/
│   │   ├── workflow.py               # @workflow decorator
│   │   ├── job.py                    # @job decorator, Job base class
│   │   ├── step.py                   # Step, run(), uses()
│   │   ├── matrix.py                 # Matrix builder
│   │   ├── conditions.py             # Push(), Branch(), etc.
│   │   └── expressions.py            # secrets, github, env contexts
│   ├── codegen/
│   │   ├── action_parser.py          # Parse action.yml files
│   │   └── generator.py              # Generate Action wrappers
│   ├── actions/                      # GENERATED action wrappers
│   │   ├── checkout.py
│   │   ├── setup_python.py
│   │   ├── cache.py
│   │   ├── upload_artifact.py
│   │   └── ...
│   └── presets/                      # Common workflow patterns
│       ├── python_ci.py
│       ├── node_ci.py
│       ├── docker_build.py
│       └── release.py
├── scripts/
│   ├── fetch_actions.sh              # Download popular action.yml files
│   └── regenerate.sh
└── pyproject.toml
```

---

## Implementation Path

### Phase 1: Core Framework + Proof of Concept

- Parse GitHub workflow JSON schema
- Implement `@workflow`, `@job` decorators
- Implement `run()` step helper
- Implement basic conditions (`if:`)
- Generate valid workflow YAML
- Test with real GitHub repository

### Phase 2: Action Wrappers

- Parse action.yml files for popular actions
- Generate typed wrappers for top 20 actions
- Implement action input validation
- Implement action output references

### Phase 3: Advanced Features

- Matrix builds with full exclude/include support
- Job output references
- Reusable workflow generation
- Secret declaration and validation
- Expression builder (type-safe `${{ }}`)

### Phase 4: Presets and Ecosystem

- Preset patterns (PythonCI, NodeCI, DockerBuild)
- CLI tooling (`wetwire validate --domain actions`, `wetwire lint`)
- VS Code extension for preview
- GitHub marketplace action for validation

---

## Viability Assessment

| Factor | Assessment | Notes |
|--------|------------|-------|
| Schema source | **Good** | action.yml + workflow JSON schema |
| User base | **Excellent** | Millions of GitHub users |
| Pain point | **Excellent** | "GitHub Actions YAML hell" is a meme |
| Type safety value | **High** | Action inputs, job refs, secrets |
| Cross-references | **Good** | Job needs, outputs, matrix vars |
| Native tooling | **Excellent** | Push YAML, GitHub runs it |

### Value Proposition

**wetwire-actions adds value by:**
1. **Type-safe action inputs** — Catch typos before push
2. **Job references** — `needs = TestJob` not `needs: test`
3. **Matrix as data** — Python lists/dicts, not YAML syntax
4. **Conditions as code** — `Push() & Branch("main")` not expression strings
5. **Secret validation** — Declared secrets, validated references
6. **Presets** — `PythonCI`, `DockerBuild` one-liners

**What it does NOT do:**
- Execute workflows (GitHub does that)
- Replace GitHub Actions (generates YAML for it)
- Provide a runner (synthesis only)

---

## Comparison to Existing Tools

### act (local runner)

Runs GitHub Actions locally. Orthogonal — we generate YAML, act runs it.

### Dagger

CI as code with containers. Different approach — Dagger is a runtime, not synthesis.

### Earthly

Build system with caching. Different scope — Earthly replaces Make, not Actions.

### actionlint

Linter for workflow YAML. Complementary — we could generate YAML that passes actionlint.

---

## Conclusion

**Recommendation: Proceed with wetwire-actions.**

| Factor | Assessment |
|--------|------------|
| **Pain point** | Severe — "YAML hell" is the #1 GitHub Actions complaint |
| **Schema source** | Available — action.yml and workflow JSON schema |
| **User base** | Massive — every GitHub user |
| **Type safety value** | High — action inputs, job refs, matrix vars, secrets |
| **Differentiation** | Clear — no Python dataclass approach exists |

**The opportunity:** GitHub Actions is used by millions, everyone complains about the YAML, and no one has applied the dataclass wrapper pattern to it yet.

**Next step:** Build Phase 1 proof of concept — implement core decorators, generate YAML for a real Python CI workflow, push to GitHub, verify it runs.

---

**Part of the Wetwire Framework** — See DRAFT_DECLARATIVE_DATACLASS_FRAMEWORK.md for the universal pattern.

---

## Sources

- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [GitHub Workflow JSON Schema](https://json.schemastore.org/github-workflow.json)
- [Creating Actions - Metadata Syntax](https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions)
- [GitHub Actions Marketplace](https://github.com/marketplace?type=actions)
