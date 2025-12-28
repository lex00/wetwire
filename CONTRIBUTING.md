# Contributing to Wetwire

Thank you for your interest in contributing to Wetwire! This document provides guidelines and information for contributors.

## Project Structure

Wetwire is a monorepo containing multiple packages across different languages:

```
wetwire/
├── docs/                    # Language-agnostic documentation
│   ├── spec/               # Specifications
│   ├── architecture/       # Architecture docs
│   └── personas/           # Agent testing personas
│
├── python/                  # Python implementation
│   └── packages/
│       └── wetwire-aws/    # AWS CloudFormation synthesis
│
├── go/                      # Go implementation (future)
├── rust/                    # Rust implementation (future)
└── typescript/              # TypeScript implementation (future)
```

## Getting Started

### Prerequisites

- Python 3.11+
- Git

### Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/wetwire.git
cd wetwire

# Set up Python development environment
cd python
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
cd packages/wetwire-aws
uv sync --group dev --group codegen
./scripts/dev-setup.sh  # Generate resources
```

## Types of Contributions

### Documentation

Documentation improvements are always welcome:

- Fix typos or clarify explanations
- Add examples
- Improve specifications
- Translate documentation

### Bug Reports

When filing a bug report, please include:

1. Package name and version
2. Python version
3. Minimal reproduction case
4. Expected behavior
5. Actual behavior

### Feature Requests

Before proposing a feature:

1. Check existing issues and discussions
2. Consider if it fits the wetwire philosophy (flat, type-safe, readable)
3. For new resource types, check if they exist in the cloud provider spec

### Code Contributions

#### For Python packages

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## Code Style

### Python

- Follow PEP 8
- Use type hints for all public APIs
- Maximum line length: 88 characters (Black default)
- Use `ruff` for linting
- Use `black` for formatting
- Use `mypy` for type checking

```bash
# Run formatters and linters
ruff check .
black .
mypy .
```

### Documentation

- Use Markdown for all documentation
- Follow the existing structure and style
- Keep specifications precise and unambiguous
- Include examples where helpful

## Testing

### Running Tests

```bash
# Run all tests
cd python/packages/wetwire-aws
uv run pytest

# Run with coverage
uv run pytest --cov

# Run type checks
uv run mypy src/wetwire_aws
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use descriptive test names: `test_ref_detects_class_reference`
- Include both positive and negative test cases
- Test edge cases (Optional, Union, forward references)

## Pull Request Process

1. **Before submitting:**
   - Ensure all tests pass
   - Run linters and formatters
   - Update documentation if needed
   - Add changelog entry if applicable

2. **PR description should include:**
   - Summary of changes
   - Related issue number (if any)
   - Testing performed
   - Breaking changes (if any)

3. **Review process:**
   - All PRs require at least one review
   - Address review feedback
   - Maintain a clean commit history

## Package-Specific Guidelines

### wetwire-aws

Contributions should:

- Maintain the flat, no-parens philosophy
- Follow patterns in existing code
- Include lint rules for best practices
- Add appropriate security checks
- Use typed property types instead of raw dicts

## Commit Messages

Use clear, descriptive commit messages:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no code change
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

Examples:
```
feat(wetwire-aws): add support for RDS Aurora clusters

fix(wetwire-aws): correct S3 bucket encryption serialization

docs: clarify forward reference behavior
```

## Architecture Decisions

Significant architectural changes should:

1. Be discussed in an issue first
2. Reference the relevant specification
3. Consider impact on all language implementations
4. Update architecture documentation

## Releasing

Releases are managed by maintainers. The process:

1. Update version numbers
2. Update changelog
3. Create release PR
4. Tag release after merge
5. Publish to PyPI

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Assume good intentions

## Questions?

- Open a GitHub issue for bugs or features
- Start a GitHub discussion for questions
- Check existing documentation first

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 license.
