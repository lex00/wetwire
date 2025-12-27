# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-12-26

### Added

- Initial release
- Core `@wetwire` decorator with `@dataclass_transform` support
- `ResourceRegistry` for tracking decorated classes
- `Template` base class for infrastructure templates
- `Provider` abstract base class for domain-specific implementations
- `Context` for environment/project context injection
- `computed` decorator for derived field values
- `when`/`match` conditionals for environment-specific values
- Ordering utilities:
  - `topological_sort()` for dependency ordering
  - `get_creation_order()` / `get_deletion_order()`
  - `detect_cycles()` for circular dependency detection
  - `get_dependency_graph()` for graph extraction
- Integration with `graph-refs` for typed references
- Python 3.11+ support
- Type checker compatibility (mypy, pyright)

[unreleased]: https://github.com/lex00/wetwire/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/lex00/wetwire/releases/tag/v0.1.0
