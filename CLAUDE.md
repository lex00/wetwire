# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Agent Workflows

**Key Tools:**
- `wetwire-aws init -o <dir>/` - Create new project skeleton
- `wetwire-aws import <template> -o <output>` - Import CloudFormation YAML/JSON
- `wetwire-aws lint <path> [--fix]` - Lint and auto-fix code style issues

**Always validate after generating code:**
```python
template = CloudFormationTemplate.from_registry()
errors = template.validate()
assert errors == []
```

---

## Project Overview

Wetwire is a unified framework for **declarative infrastructure-as-code** using native language constructs. The `wetwire-aws` package provides AWS CloudFormation synthesis using **dataclasses as a declarative interface**.

**Core Innovation**: Wrapper dataclasses with declarative wiring where all infrastructure relationships are defined as typed field declarations, not imperative code.

## Architecture Principles

### The Wrapper Dataclass Pattern

Every CloudFormation resource is wrapped in a user-defined dataclass with a `resource:` field:

```python
from . import *

@wetwire_aws
class MyVPC:
    resource: ec2.VPC
    cidr_block: str = "10.0.0.0/16"
    enable_dns_hostnames: bool = True

@wetwire_aws
class MySubnet:
    resource: ec2.Subnet
    cidr_block: str = "10.0.1.0/24"
    vpc_id = ref(MyVPC)  # Cross-resource reference via ref() helper
```

**Key point**: ALL wiring happens inside dataclass field declarations, not at instantiation.

### Code Generation Strategy

All AWS resource classes are **generated at build time** from CloudFormation specs. Resources are NOT committed to git - they're generated when building the wheel.

**Rationale**:
- Clean git history (no 50MB+ of generated code)
- Minimal runtime dependencies (wetwire + pyyaml)
- IDE autocomplete works after local `./scripts/regenerate.sh`
- Published wheels contain pre-generated resources
- Reproducible builds from CloudFormation spec

### Type System

- **CloudFormation → Python mappings**: String→str, Integer→int, Boolean→bool, etc.
- **Union types for intrinsics**: Every property accepts literal values OR CloudFormation functions (Ref, GetAtt, Sub, etc.)
- **PascalCase → snake_case**: CloudFormation properties like `BucketName` become `bucket_name`

### Cross-Resource References

Two reference patterns are available:

**1. Function calls (`ref()`, `get_att()`)** - Simple, direct references:
```python
from . import *

@wetwire_aws
class BucketPolicy:
    resource: s3.BucketPolicy
    bucket = ref(MyBucket)  # Direct class reference
    policy_document = get_att(MyRole, ARN)
```

**2. Type annotations (`Ref[T]`, `Attr[T, name]`)** - Enables graph-refs introspection:
```python
from . import *

@wetwire_aws
class ProcessorFunction:
    resource: lambda_.Function
    bucket: Ref[DataBucket] = None       # Reference to resource
    role: Attr[ProcessorRole, "Arn"] = None  # GetAtt reference
```

**When to use each:**
- Use `ref()`/`get_att()` for simple cases and inline values
- Use `Ref[T]`/`Attr[T, name]` when you need dependency introspection, topological sorting, or cross-file references with `setup_resources()`

### Multi-File Organization with setup_resources()

For multi-file projects, use `setup_resources()` for automatic discovery:

```python
# myapp/__init__.py
from wetwire_aws.loader import setup_resources
setup_resources(__file__, __name__, globals())
```

This automatically:
- Discovers all `.py` files in the package
- Parses them to find class definitions and `Ref[T]`/`Attr[T, ...]` references
- Loads modules in dependency order (dependencies first)
- Injects classes into each module's namespace before it loads
- Generates `.pyi` stubs for IDE autocomplete

**Resource files use the single import pattern:**
```python
# myapp/compute.py
from . import *

__all__ = ["ProcessorFunction"]

@wetwire_aws
class ProcessorFunction:
    resource: lambda_.Function
    # ProcessorRole is injected by setup_resources() - defined in another file
    role: Attr[ProcessorRole, "Arn"] = None  # noqa: F821
```

See `python/packages/wetwire/docs/package-structure.md` for complete documentation.

**Qualified resource types for name collisions:**

When a wrapper class has the same name as the AWS resource class (e.g., `class Bucket` wrapping `s3.Bucket`), the module-qualified type avoids self-reference:

```python
from . import *

@wetwire_aws
class Bucket:
    resource: s3.Bucket  # NOT resource: Bucket (would be self-referential)
    bucket_name = "my-bucket"
```

All resource types should use module-qualified names: `s3.Bucket`, `ec2.Instance`, `lambda_.Function`, etc.

### Validation Strategy (Two-Layer)

1. **Static Type Checking** (mypy/pyright) - Catches type errors at development time
2. **CloudFormation Validation** - AWS validates during deployment/template validation

**No Pydantic or runtime validation libraries** - keeps dependencies minimal, lets CloudFormation be the source of truth.

## Project Structure

```
python/packages/
├── wetwire/                 # Core framework (cloud-agnostic)
│   └── src/wetwire/
│       ├── decorator.py     # @wetwire decorator
│       ├── registry.py      # Resource registration
│       ├── template.py      # Base template class
│       ├── loader.py        # setup_resources() for multi-file packages
│       ├── stubs.py         # StubConfig, .pyi generation for IDE support
│       └── codegen/         # Shared codegen utilities
│           ├── schema.py    # IntermediateSchema, PropertyDef, etc.
│           ├── transforms.py # to_snake_case, keyword escaping
│           ├── fetcher.py   # HTTP fetching utilities
│           └── generator.py # Code generation utilities
│
├── wetwire-aws/             # AWS domain package
│   ├── src/wetwire_aws/
│   │   ├── base.py          # CloudFormationResource base
│   │   ├── decorator.py     # @wetwire_aws decorator
│   │   ├── template.py      # CloudFormationTemplate
│   │   ├── loader.py        # AWS-specific setup_resources() wrapper
│   │   ├── stubs.py         # AWS_STUB_CONFIG for stub generation
│   │   ├── intrinsics/      # Ref, GetAtt, Sub, etc.
│   │   └── resources/       # GENERATED at build time (not in git)
│   │       ├── s3/
│   │       ├── ec2/
│   │       └── ...          # ~260 service modules
│   ├── codegen/             # AWS-specific code generation
│   │   ├── config.py        # CF spec URL, service priorities
│   │   ├── fetch.py         # Download CloudFormation specs
│   │   ├── parse.py         # Parse CF spec to intermediate format
│   │   ├── extract_enums.py # Extract enums from botocore
│   │   └── generate.py      # Generate Python dataclasses
│   ├── scripts/
│   │   ├── regenerate.sh    # Run codegen pipeline
│   │   └── ci.sh            # Local CI checks
│   └── hatch_build.py       # Build hook (runs codegen)
│
└── wetwire-gcp/             # GCP domain package (future)
```

**wetwire.codegen** provides shared codegen utilities that can be reused by any domain package.
Install with: `pip install wetwire[codegen]`

## Development Commands

### Setup

```bash
# Clone and install development dependencies
uv sync --all-extras
```

### Code Generation

```bash
# Regenerate ALL AWS resource classes from latest CloudFormation spec
cd python/packages/wetwire-aws
./scripts/regenerate.sh

# Or manually (4-stage pipeline):
uv run python -m codegen.fetch        # Download CloudFormation spec
uv run python -m codegen.parse        # Parse to intermediate format
uv run python -m codegen.extract_enums # Extract enums from botocore
uv run python -m codegen.generate     # Generate Python dataclasses

# Force re-fetch even if spec is fresh
./scripts/regenerate.sh --force

# Dry run (show what would be generated)
./scripts/regenerate.sh --dry-run
```

### Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ -v --cov

# Run specific test file
uv run pytest tests/test_s3.py -v

# Run specific test
uv run pytest tests/test_s3.py::test_bucket_serialization -v
```

### Type Checking

```bash
# Type check entire codebase
uv run mypy src/wetwire_aws/

# Type check specific module
uv run mypy src/wetwire_aws/core/
```

### Linting and Formatting

```bash
# Format code
uv run black src/ tests/

# Lint
uv run ruff check src/ tests/
```

### Building

```bash
# Full build pipeline (download spec, generate, format, test, build)
./scripts/build.sh

# Build package only
uv build
```

## Critical Implementation Rules

### 1. Block/Wrapper Syntax (Not Imperative)

**ALWAYS use wrapper dataclasses** - never use imperative instantiation:

```python
from . import *

# ✅ CORRECT - Block syntax with wrapper
@wetwire_aws
class MyBucket:
    resource: s3.Bucket
    bucket_name: str = "my-bucket"

my_bucket = MyBucket()

# ❌ WRONG - Imperative syntax
bucket = s3.Bucket(bucket_name="my-bucket")
```

### 2. Resource Naming

CloudFormation resource names do NOT include service prefixes:
- Class name: `Instance` (not `EC2Instance`)
- Namespacing via module qualification: `ec2.Instance`, `s3.Bucket`

### 3. Generated Code Management

- Generated files in `src/wetwire_aws/resources/` are **NOT committed to git** - generated at build time
- Every generated file includes a header: `⚠️ AUTO-GENERATED FILE - DO NOT EDIT MANUALLY`
- Never manually edit generated files - regenerate instead
- Run `./scripts/regenerate.sh` for local development

### 4. Dependencies

**Runtime dependencies**:
- `wetwire` - Core framework
- `pyyaml` - Required for YAML template parsing and serialization

**Codegen dependencies** (build-time only):
- `requests` - Download CloudFormation specs
- `jinja2` - Template rendering
- `botocore` - Extract enum values from AWS SDK
- `black` - Format generated code

**Development dependencies**:
- `mypy`, `pyright` - Static type checking
- `pytest`, `pytest-cov` - Testing
- `ruff` - Linting and formatting

### 5. Python Version

Requires Python 3.11+ for modern type annotation features.

## Code Generation Algorithm

When modifying the code generator (`python/packages/wetwire-aws/codegen/generate.py`):

1. **Parse CloudFormation spec** - JSON structure with ResourceTypes and PropertyTypes
2. **Generate nested property classes first** - Complex property types become dataclasses
3. **Map CloudFormation types to Python types** - String→str, Integer→int, Boolean→bool, Json→Dict[str, Any], etc.
4. **Convert PascalCase to snake_case** - With special handling for acronyms (VPCId → vpc_id)
5. **Handle Python keywords** - Append underscore if needed (type → type_)
6. **Create Union types** - Allow literals OR intrinsic functions for each property
7. **Generate typed attribute accessors** - @property methods for GetAtt attributes
8. **Add docstrings** - From CloudFormation documentation
9. **Format with Black** - Ensure consistent code style

## Package Build and Distribution

### Build System

- Uses **hatch** as build backend with custom build hook
- Build hook (`hatch_build.py`) runs codegen pipeline automatically during `hatch build`
- Src-layout: `src/wetwire_aws/` for proper isolation
- Uses **uv** for local development and dependency management

### Build-Time Generation

Resources are generated at build time, not pre-committed:

1. `hatch build` triggers custom build hook
2. Build hook runs 4-stage codegen pipeline (fetch → parse → extract_enums → generate)
3. Generated resources are included in wheel via `force_include`
4. Skip codegen with `WETWIRE_SKIP_CODEGEN=1` if resources already exist

### CI/CD Workflows

- **CI** (`.github/workflows/wetwire-aws-ci.yml`): Generates resources once, shares via artifact, runs tests across Python 3.11-3.13
- **Release** (`.github/workflows/wetwire-aws-release.yml`): Builds wheel, publishes to PyPI on tag

### Local Development

```bash
cd python/packages/wetwire-aws
./scripts/regenerate.sh    # Generate resources
./scripts/ci.sh            # Run same checks as CI
./scripts/ci.sh --quick    # Skip regeneration if already done
```

## Understanding the Codebase

### Key Concepts

1. **CloudFormationResource** - Base class for all AWS resources, provides:
   - `resource_type: ClassVar[str]` - AWS resource type (e.g., "AWS::S3::Bucket")
   - `to_dict()` - Serialize to CloudFormation JSON
   - `ref()` - Create Ref intrinsic function
   - `get_att()` - Create GetAtt intrinsic function
   - Auto-naming via `resource_name` property
   - Tag merging via `all_tags` property

2. **DeploymentContext** - Provides environment defaults:
   - Project name, component, environment, region, account_id
   - Auto-generates resource names (e.g., "MyProject-MyComponent-MyBucket-prod-001-blue-us-east-1")
   - Merges tags across context and resources

3. **Intrinsic Functions** - Type-safe CloudFormation functions:
   - `Ref` - Reference to logical ID
   - `GetAtt` - Get resource attribute
   - `Sub` - String substitution
   - `Join`, `If`, `Select`, etc.

4. **Template** - Container for CloudFormation template:
   - Add resources, parameters, outputs, conditions
   - Serialize to JSON/YAML
   - Optional validation via AWS API

### Reading Generated Code

Generated files follow this pattern:

```python
# Header with generation metadata
"""AWS CloudFormation EC2 Resources
⚠️ AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
CloudFormation Spec: 2025.12.11
Generator Version: 1.0.0
Generated: 2024-12-15T13:18:57Z
"""

# Nested property type dataclasses first
@dataclass
class PropertyTypeClass:
    field: Optional[Union[str, Ref]] = None

# Main resource class
@dataclass
class ResourceClass(CloudFormationResource):
    resource_type: ClassVar[str] = "AWS::Service::Resource"

    # Properties (snake_case)
    property_name: Optional[Union[str, Ref, GetAtt]] = None

    # Typed attribute accessors
    @property
    def attr_name(self) -> GetAtt:
        return self.get_att("AttributeName")
```

## Testing Strategy

### Test Structure

- `tests/test_generated_*.py` - Test generated AWS resource classes
- Use wrapper dataclass pattern in test fixtures
- Verify serialization to CloudFormation JSON
- Test intrinsic function serialization
- Include mypy type error tests (files that should fail type checking)

### Example Test Pattern

```python
from wetwire_aws.resources import s3

# Define wrapper dataclasses at module level
@wetwire_aws
class TestBucket:
    resource: s3.Bucket
    bucket_name: str = "test-bucket"

def test_serialization():
    bucket = TestBucket()
    result = bucket.to_dict()
    assert result["Type"] == "AWS::S3::Bucket"
    assert result["Properties"]["BucketName"] == "test-bucket"
```

## Important References

- AWS CloudFormation Resource Specification: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-resource-specification.html
- Specification JSON: https://d1uauaxba7bl26.cloudfront.net/latest/gzip/CloudFormationResourceSpecification.json

## Anti-Patterns to Avoid

When generating code for this library, NEVER use raw CloudFormation dict patterns.

### 1. Raw Intrinsic Function Dicts
```python
# ❌ WRONG - raw dict
vpc_id = {"Ref": "VpcId"}
availability_zone = {"Fn::Select": [0, {"Fn::GetAZs": ""}]}
password = {"Fn::Sub": "${Secret}"}
joined = {"Fn::Join": [",", [...]]}

# ✅ CORRECT - typed helpers
from wetwire_aws.intrinsics import Ref, Sub, Select, GetAZs, Join
vpc_id = Ref("VpcId")
availability_zone = Select(0, GetAZs())
password = Sub("${Secret}")
joined = Join(",", [...])
```

### 2. Pseudo-Parameter References
```python
# ❌ WRONG
region = {"Ref": "AWS::Region"}
account_id = {"Ref": "AWS::AccountId"}

# ✅ CORRECT
from wetwire_aws.intrinsics import AWS_REGION, AWS_ACCOUNT_ID
region = AWS_REGION
account_id = AWS_ACCOUNT_ID
```

### 3. Inline PropertyType Constructors
```python
from . import *

# ❌ WRONG - inline constructor in list
security_group_ingress = [
    ec2.security_group.Ingress(ip_protocol=ec2.IpProtocol.TCP, from_port=443)
]

# ✅ CORRECT - separate wrapper class
@wetwire_aws
class MySecurityGroupIngress:
    resource: ec2.security_group.Ingress
    ip_protocol = ec2.IpProtocol.TCP
    from_port = 443

@wetwire_aws
class MySecurityGroup:
    resource: ec2.SecurityGroup
    security_group_ingress = [MySecurityGroupIngress]
```

### 4. Inline IAM Policies
```python
from . import *

# ❌ WRONG - inline dict
assume_role_policy_document = {
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow", ...}]
}

# ✅ CORRECT - wrapper classes
@wetwire_aws
class MyAssumeRoleStatement:
    resource: iam.PolicyStatement
    principal = {"Service": "lambda.amazonaws.com"}
    action = "sts:AssumeRole"

@wetwire_aws
class MyAssumeRolePolicy:
    resource: iam.PolicyDocument
    statement = [MyAssumeRoleStatement]

@wetwire_aws
class MyRole:
    resource: iam.Role
    assume_role_policy_document = MyAssumeRolePolicy
```

### Available Intrinsic Functions

Import from `wetwire_aws.intrinsics`:
- `Ref("ParameterName")` - Reference parameters
- `ref(ResourceClass)` - Reference resources (lowercase)
- `get_att(ResourceClass, "Attribute")` - Get resource attributes
- `Sub("string with ${variable}")` - String substitution
- `Join(",", [items])` - Join list to string
- `Select(index, list)` - Select item from list
- `GetAZs(region="")` - Get availability zones
- `AWS_REGION`, `AWS_ACCOUNT_ID`, `AWS_STACK_NAME` - Pseudo-parameters
