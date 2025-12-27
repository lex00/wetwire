# CLI Framework

The wetwire core package provides reusable CLI utilities for building domain-specific command-line tools.

## Overview

Domain packages like wetwire-aws can use these utilities to build their CLIs with consistent patterns:

| Utility | Purpose |
|---------|---------|
| `discover_resources()` | Import modules to trigger resource registration |
| `add_common_args()` | Add standard CLI arguments |
| `create_list_command()` | Create a 'list' command handler |
| `create_validate_command()` | Create a 'validate' command handler |

## Quick Example

```python
# my_domain_cli.py
import argparse
from wetwire import (
    discover_resources,
    add_common_args,
    create_list_command,
    create_validate_command,
)
from my_domain.registry import get_registry

registry = get_registry()

def get_resource_type(cls: type) -> str:
    """Extract resource type string from a class."""
    resource_cls = getattr(cls, "__annotations__", {}).get("resource")
    if resource_cls and hasattr(resource_cls, "_resource_type"):
        return resource_cls._resource_type
    return "Unknown"

def main():
    parser = argparse.ArgumentParser(prog="my-domain")
    subparsers = parser.add_subparsers(dest="command")

    # List command
    list_parser = subparsers.add_parser("list", help="List resources")
    add_common_args(list_parser)
    list_parser.set_defaults(func=create_list_command(registry, get_resource_type))

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate references")
    add_common_args(validate_parser)
    validate_parser.set_defaults(func=create_validate_command(registry))

    args = parser.parse_args()
    if args.command:
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
```

---

## API Reference

### discover_resources()

Import a module to trigger resource registration.

```python
from wetwire import discover_resources

count = discover_resources(
    module_path="myapp.infra",
    registry=my_registry,
    verbose=True,
)
print(f"Discovered {count} resources")
```

**Parameters:**
- `module_path` (str): Python module path to import
- `registry` (ResourceRegistry): Registry to count registrations
- `verbose` (bool): Print discovery info to stderr

**Returns:** Number of newly registered resources

**Raises:** SystemExit if the module cannot be imported

---

### add_common_args()

Add standard CLI arguments to a parser.

```python
from wetwire import add_common_args

parser = argparse.ArgumentParser()
add_common_args(parser)
```

**Adds these arguments:**
- `--module/-m`: Python module to import (repeatable)
- `--scope/-s`: Package scope to filter resources
- `--verbose/-v`: Enable verbose output

---

### create_list_command()

Create a 'list' command handler.

```python
from wetwire import create_list_command

def get_type(cls):
    return cls.__annotations__.get("resource", "Unknown")

list_cmd = create_list_command(registry, get_type)
```

**Parameters:**
- `registry` (ResourceRegistry): Registry to list from
- `get_resource_type` (Callable): Function to extract type string from class

**Returns:** Command handler function

**Output:**
```
Registered resources (3):

  DataBucket: AWS::S3::Bucket
  ProcessorFunction: AWS::Lambda::Function
  ProcessorRole: AWS::IAM::Role
```

---

### create_validate_command()

Create a 'validate' command handler that checks references.

```python
from wetwire import create_validate_command

validate_cmd = create_validate_command(registry)
```

**Parameters:**
- `registry` (ResourceRegistry): Registry to validate

**Returns:** Command handler function

Uses graph-refs `get_dependencies()` to find all references and validates they exist in the registry.

**Output (success):**
```
Validation passed: 5 resources OK
```

**Output (failure):**
```
Validation FAILED:
  ERROR: ProcessorFunction references MissingRole which is not registered
```

---

## Domain-Specific Commands

The `build` command is typically domain-specific because it generates output in a particular format (CloudFormation JSON, Kubernetes YAML, etc.).

Example pattern:

```python
def build_command(args: argparse.Namespace) -> None:
    """Domain-specific build command."""
    # Import modules
    if args.modules:
        for module_path in args.modules:
            discover_resources(module_path, registry, args.verbose)

    # Generate domain-specific output
    template = DomainTemplate.from_registry(scope_package=args.scope)

    if args.format == "yaml":
        print(template.to_yaml())
    else:
        print(template.to_json())
```

---

## Common Argument Patterns

### Multiple Modules

```bash
my-cli build --module myapp.network --module myapp.compute
```

### Scope Filtering

```bash
my-cli list --scope myapp.production
```

### Verbose Output

```bash
my-cli validate --module myapp.infra --verbose
```

---

## Integration with Entry Points

Register your CLI in `pyproject.toml`:

```toml
[project.scripts]
my-domain = "my_domain.cli:main"
```

---

## See Also

- [Architecture](../architecture/ARCHITECTURE.md) - Wetwire design principles
- [IDE Support](IDE_SUPPORT.md) - Type checking and IDE integration
