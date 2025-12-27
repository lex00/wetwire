# wetwire

Declarative dataclass framework for infrastructure-as-code.

## Installation

```bash
pip install wetwire
```

## Quick Start

```python
from wetwire import wetwire, Template

# Define resources with the @wetwire decorator
@wetwire
class MyNetwork:
    resource: VPC
    cidr_block = "10.0.0.0/16"

@wetwire
class MySubnet:
    resource: Subnet
    vpc = MyNetwork  # Reference to MyNetwork (no parens!)
    cidr_block = "10.0.1.0/24"

# Build a template from registered resources
template = Template.from_registry()
```

## Features

- **Declarative syntax** - Define resources as dataclasses with defaults
- **Typed references** - Use `Ref[T]` for type-safe references between resources
- **Auto-registration** - Resources automatically register for template building
- **Dependency ordering** - Automatic topological sort based on references
- **Provider abstraction** - Plug in different output formats (CloudFormation, Terraform, etc.)

## Documentation

See the [wetwire documentation](https://github.com/lex00/wetwire) for more details.

## License

Apache 2.0
