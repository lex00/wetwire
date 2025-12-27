# IDE Support & Type Checking

The wetwire pattern provides full IDE support through:
- Type annotations on all classes and functions
- Generated `.pyi` stub files for dynamic imports
- Compatibility with Pylance, mypy, and other type checkers

## The Challenge

Wetwire packages often use centralized imports for clean, concise code:

```python
from . import *  # noqa: F403, F401

@wetwire
class MyResource:
    resource: SomeType
    other: Ref[OtherResource] = None  # Available without explicit import
```

This works at runtime because the package's `__init__.py` dynamically exports all necessary symbols. However, IDEs like VSCode/Pylance can't see these dynamic exports without help.

## The Solution: .pyi Stub Files

Type stub files (`.pyi`) declare what a module exports. When placed alongside `__init__.py`, they tell the IDE:

- What names are available via star imports
- Type information for all exported classes
- Re-exports from wetwire packages

```
myproject/
├── __init__.py      # Your code with dynamic exports
├── __init__.pyi     # Generated stub (declares exports)
├── resources.py
└── policies.py
```

### Example Stub File

```python
# __init__.pyi (generated)
from wetwire import wetwire as wetwire
from wetwire import Ref as Ref
from wetwire import Attr as Attr

# For wetwire-aws projects:
from wetwire_aws import wetwire_aws as wetwire_aws
from wetwire_aws import ref as ref
from wetwire_aws import get_att as get_att

from .resources import MyBucket as MyBucket
from .resources import MyFunction as MyFunction
from .policies import MyPolicy as MyPolicy
```

This enables:
- IDE autocomplete for `MyBucket`, `MyFunction`, etc.
- Type checking for reference annotations
- Error detection for undefined references

## Generating Stub Files

Stub files can be generated manually or with tooling. A typical stub file exports all symbols that should be available:

```python
# my_project/__init__.pyi
# Re-export all resource classes
from .storage import DataBucket as DataBucket
from .compute import ProcessorFunction as ProcessorFunction

# Re-export wetwire types
from wetwire import Ref as Ref, Attr as Attr
from wetwire_aws import wetwire_aws as wetwire_aws
```

### When to Regenerate

Regenerate stubs after:
- Creating new resource classes
- Adding new parameters or outputs
- Renaming classes
- Modifying package-level imports

## VSCode/Pylance Setup

Pylance should work automatically once stubs are generated. If you see "unknown" errors:

1. Ensure stubs are generated
2. Reload VSCode window: Cmd/Ctrl+Shift+P → "Reload Window"
3. Check Python interpreter is set to your venv

### Settings

For best results, add to `.vscode/settings.json`:

```json
{
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.diagnosticSeverityOverrides": {
    "reportUnusedImport": "warning"
  }
}
```

## mypy Configuration

For mypy type checking, add to `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_ignores = true
ignore_missing_imports = true
```

Or use `mypy.ini`:

```ini
[mypy]
python_version = 3.10
warn_return_any = True
warn_unused_ignores = True
ignore_missing_imports = True
```

## Handling Star Import Warnings

Add `# noqa` comments to suppress flake8/ruff warnings:

```python
from . import *  # noqa: F403, F401
```

These warnings are expected for the wetwire pattern. The stub files ensure type safety despite the dynamic imports.

## Troubleshooting

### "Cannot find module" errors

- Ensure stub files exist (`.pyi` alongside `__init__.py`)
- Regenerate stub files if they're missing
- Check you're in the correct virtual environment

### Stubs out of date

- Regenerate stubs after adding/renaming classes
- Keep stubs in sync during active development

### IDE shows "partially unknown" types

- Regenerate stubs and reload IDE
- Check that generated `.pyi` files include your new classes
- Verify the package's `__init__.py` properly exports all symbols

### Star import not recognized

Some type checkers struggle with `from . import *`. If issues persist:

1. Ensure stub file lists all exports explicitly
2. Use `as` aliases: `from .resources import MyBucket as MyBucket`
3. Consider explicit imports for critical symbols

## Best Practices

1. **Commit stub files**: Include `.pyi` files in version control for team consistency
2. **CI validation**: Run type checking in CI to catch issues early
3. **Keep stubs updated**: Regenerate when adding or renaming resources
4. **Explicit re-exports**: Use `as` aliasing in stubs for clarity

## See Also

- [Architecture](../architecture/ARCHITECTURE.md) - Wetwire design principles
- Package-specific documentation for stub generation commands
