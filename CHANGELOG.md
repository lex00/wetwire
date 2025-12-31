# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.3] - 2024-12-31

### Added

- Auto-decoration support for cross-file references via `_update_attr_refs()`
- Invisible decorator pattern: classes with `resource:` annotation are auto-decorated

### Changed

- `cross_file_test` package now uses decorator-free pattern as canonical example
- Documentation examples updated to show decorator-free wrapper pattern

## [0.1.2] - 2024-12-29

### Added

- `wetwire-aws init` command for scaffolding new packages
- New lint rules for detecting inline patterns that should be wrapper classes:
  - WAW013: Inline PropertyType constructors
  - WAW014: Inline PolicyDocument dicts
  - WAW015: Inline SecurityGroup rules
  - WAW016: Inline PolicyStatement dicts
  - WAW017: Inline dicts for property type fields (suffix-based detection)
  - WAW018: Redundant relative imports with `from . import *`

### Changed

- Bump `dataclass-dsl` dependency to 0.1.3

### Fixed

- PropertyType wrapper serialization (no-parens style)
- Linter enum checks for case-insensitive key matching

## [0.1.1] - 2024-12-28

### Fixed

- PropertyType wrapper serialization and linter enum checks

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
- Integration with `dataclass-dsl` for typed references
- Python 3.11+ support
- Type checker compatibility (mypy, pyright)

[unreleased]: https://github.com/lex00/wetwire/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/lex00/wetwire/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/lex00/wetwire/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/lex00/wetwire/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/lex00/wetwire/releases/tag/v0.1.0
