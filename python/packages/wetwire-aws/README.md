# wetwire-aws

AWS CloudFormation synthesis using Python dataclasses.

## Installation

```bash
pip install wetwire-aws
```

## Quick Example

```python
from wetwire_aws.loader import setup_resources
setup_resources(__file__, __name__, globals())
```

```python
# infra.py
from . import *

@wetwire_aws
class MyBucket:
    resource: s3.Bucket
    bucket_name = "my-data"

@wetwire_aws
class MyFunction:
    resource: lambda_.Function
    function_name = "processor"
    runtime = lambda_.Runtime.PYTHON3_12
    role = MyRole.Arn  # Type-safe reference
```

```bash
wetwire-aws build --module myapp > template.json
```

## Documentation

- [Quick Start](docs/QUICK_START.md) - Full tutorial
- [CLI Reference](docs/CLI.md) - All commands
- [Comparison](docs/COMPARISON.md) - vs CDK, Terraform

## Development

```bash
cd python/packages/wetwire-aws
uv sync
./scripts/dev-setup.sh    # First-time setup (generate resources)
./scripts/regenerate.sh   # Re-generate resources (after spec updates)
uv run pytest             # Run tests
```

See [Developer Guide](docs/DEVELOPERS.md) for details.

## License

Apache 2.0
