# Wetwire Package Structure Guide

## Overview

wetwire enables multi-file resource organization with automatic dependency resolution and IDE support through stub generation.

The key feature is the **single import pattern**: every resource file uses `from . import *` to get all resources, decorators, and types.

## Recommended Project Structure

```
myproject/
├── pyproject.toml
└── src/myproject/
    └── resources/           # Your resource definitions
        ├── __init__.py      # Uses setup_resources()
        ├── __init__.pyi     # Auto-generated for IDE support
        ├── network.py       # VPC, Subnet, etc.
        ├── compute.py       # Lambda, EC2 with cross-file refs
        └── storage.py       # S3, DynamoDB
```

## Setting Up a Resource Package

### Step 1: Create `__init__.py`

```python
# src/myproject/resources/__init__.py
from wetwire_aws.loader import setup_resources

setup_resources(__file__, __name__, globals())
```

That's it. `setup_resources()` handles:
1. Discovering all `.py` files in the package
2. Parsing them to find class definitions and references
3. Building a dependency graph from `Ref[T]`, `Attr[T, ...]` annotations
4. Importing modules in topological order
5. Generating `.pyi` stubs for IDE autocomplete

### Step 2: Define Resources in Separate Files

Each file uses `from . import *` to get all injected classes.

```python
# src/myproject/resources/network.py
from . import *

__all__ = ["AppVPC", "PublicSubnet"]


@wetwire_aws
class AppVPC:
    resource: ec2.VPC
    cidr_block = "10.0.0.0/16"


@wetwire_aws
class PublicSubnet:
    resource: ec2.Subnet
    vpc: Ref[AppVPC]  # Reference resolved across files
    cidr_block = "10.0.1.0/24"
```

```python
# src/myproject/resources/compute.py
from . import *

__all__ = ["AppRole", "AppFunction"]


@wetwire_aws
class AppRole:
    resource: iam.Role
    role_name = "app-role"


@wetwire_aws
class AppFunction:
    resource: lambda_.Function
    function_name = "app-handler"
    runtime = lambda_.Runtime.PYTHON3_12
    # Cross-file reference using Attr annotation
    # AppRole is injected before this module loads
    role: Attr[AppRole, "Arn"] = None  # noqa: F821
```

### Step 3: Use Your Resources

```python
# main.py
from myproject.resources import AppVPC, PublicSubnet, AppRole, AppFunction
from myproject.resources import CloudFormationTemplate

# All resources are available
template = CloudFormationTemplate.from_registry()
print(template.to_json())
```

## How It Works

### 1. Dependency Detection

`setup_resources()` parses source files to find type annotations:
- `Ref[ClassName]` - Direct reference
- `Attr[ClassName, "attribute"]` - GetAtt reference
- `RefList[ClassName]` - List of references
- `RefDict[str, ClassName]` - Dict of references

### 2. Topological Sorting

Modules are imported in dependency order using Kahn's algorithm:
- If `compute.py` references `network.py`, network loads first
- Cycles are detected and broken gracefully

### 3. Namespace Injection

Before each module executes, already-loaded classes are injected into its namespace. This makes `Attr[AppRole, "Arn"]` work even when `AppRole` is in another file.

The injection includes:
- All AWS service modules (`s3`, `ec2`, `iam`, `lambda_`, etc.)
- The `@wetwire_aws` decorator
- Reference types (`Ref`, `Attr`, `RefList`, `RefDict`)
- Helper functions (`ref`, `get_att`, `ARN`)
- Template classes (`CloudFormationTemplate`)

### 4. Stub Generation

A `.pyi` file is auto-generated for IDE support:

```python
# __init__.pyi (auto-generated)
"""Auto-generated stub for IDE type checking."""

from .network import AppVPC as AppVPC
from .network import PublicSubnet as PublicSubnet
from .compute import AppRole as AppRole
from .compute import AppFunction as AppFunction

__all__: list[str] = ['AppFunction', 'AppRole', 'AppVPC', 'PublicSubnet']
```

## IDE Configuration

### VS Code / Pylance

The stubs are detected automatically. If you have issues, add to `pyrightconfig.json`:

```json
{
  "stubPath": "src"
}
```

### PyCharm

Stubs are detected automatically from the package directory.

## Disabling Stub Generation

If you don't want automatic stub generation:

```python
setup_resources(__file__, __name__, globals(), generate_stubs=False)
```

## Domain Package Support

The `setup_resources()` function is domain-agnostic. Each domain package provides a wrapper with appropriate configuration:

```python
# wetwire-aws provides:
from wetwire_aws.loader import setup_resources

# Future packages will provide:
# from wetwire_gcp.loader import setup_resources
# from wetwire_azure.loader import setup_resources
```

## Troubleshooting

### "NameError: name 'ClassName' is not defined"

This means `setup_resources()` couldn't find the class. Check:
1. Is `__all__` defined in the file containing the class?
2. Is the class decorated with `@wetwire_aws`?
3. Does the file name start with `_`? (underscore files are skipped)

### IDE shows errors but code works

Regenerate stubs by calling `setup_resources()` again (happens on import).

### Circular dependencies

`setup_resources()` handles cycles by breaking them at the most-referenced class. If you have issues, consider restructuring to reduce cycles.
