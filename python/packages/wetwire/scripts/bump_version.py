#!/usr/bin/env python3
"""Bump version in pyproject.toml and __init__.py.

Usage:
    python scripts/bump_version.py patch   # 0.1.0 → 0.1.1
    python scripts/bump_version.py minor   # 0.1.0 → 0.2.0
    python scripts/bump_version.py major   # 0.1.0 → 1.0.0
    python scripts/bump_version.py 2.0.0   # Set specific version
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent
PYPROJECT = PROJECT_ROOT / "pyproject.toml"
INIT_FILE = PROJECT_ROOT / "src" / "wetwire" / "__init__.py"

VERSION_PATTERN = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def get_current_version() -> str:
    """Read current version from pyproject.toml."""
    content = PYPROJECT.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse version string into (major, minor, patch)."""
    match = VERSION_PATTERN.match(version)
    if not match:
        raise ValueError(f"Invalid version format: {version}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump_version(current: str, bump_type: str) -> str:
    """Calculate new version based on bump type."""
    major, minor, patch = parse_version(current)

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        # Assume it's a specific version string
        parse_version(bump_type)  # Validate format
        return bump_type


def update_pyproject(new_version: str) -> None:
    """Update version in pyproject.toml."""
    content = PYPROJECT.read_text()
    updated = re.sub(
        r'^(version\s*=\s*")[^"]+(")',
        rf"\g<1>{new_version}\g<2>",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    PYPROJECT.write_text(updated)


def update_init(new_version: str) -> None:
    """Update __version__ in __init__.py."""
    content = INIT_FILE.read_text()
    updated = re.sub(
        r'^(__version__\s*=\s*")[^"]+(")',
        rf"\g<1>{new_version}\g<2>",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    INIT_FILE.write_text(updated)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1

    bump_type = sys.argv[1]

    if bump_type in ("-h", "--help"):
        print(__doc__)
        return 0

    current = get_current_version()
    new = bump_version(current, bump_type)

    print(f"Bumping version: {current} -> {new}")

    update_pyproject(new)
    print(f"  Updated {PYPROJECT.relative_to(PROJECT_ROOT)}")

    update_init(new)
    print(f"  Updated {INIT_FILE.relative_to(PROJECT_ROOT)}")

    print(f"\nVersion bumped to {new}")
    print("Don't forget to update CHANGELOG.md!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
