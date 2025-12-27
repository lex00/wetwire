# wetwire

Core framework for declarative infrastructure-as-code using Python dataclasses.

## Overview

wetwire provides the foundation for defining infrastructure resources declaratively. It's designed to be extended by domain-specific packages:

- **wetwire-aws** - AWS CloudFormation resources
- **wetwire-gcp** - GCP resources (planned)
- **wetwire-azure** - Azure resources (planned)

## Installation

For AWS infrastructure, install wetwire-aws (which includes wetwire):

```bash
pip install wetwire-aws
```

For the core framework only:

```bash
pip install wetwire
```

## Usage

See the [wetwire-aws documentation](../wetwire-aws/README.md) for usage with AWS CloudFormation.

## Core Features

- **@wetwire decorator** - Transforms classes into infrastructure resources
- **setup_resources()** - Multi-file organization with automatic dependency resolution
- **Reference types** - `Ref[T]`, `Attr[T, name]` for typed cross-resource references
- **Stub generation** - Automatic `.pyi` generation for IDE support
- **Provider abstraction** - Plug in different output formats

## Package Structure

wetwire enables the single-import pattern for multi-file projects:

```python
# myapp/__init__.py
from wetwire_aws.loader import setup_resources
setup_resources(__file__, __name__, globals())
```

```python
# myapp/storage.py
from . import *

@wetwire_aws
class DataBucket:
    resource: s3.Bucket
    bucket_name = "data"
```

See [package-structure.md](docs/package-structure.md) for details.

## License

Apache 2.0
