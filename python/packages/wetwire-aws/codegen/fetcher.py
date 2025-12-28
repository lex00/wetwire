"""
Fetcher utilities for codegen pipeline.

This module provides utilities for fetching source materials
(CloudFormation specs, package versions) during code generation.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable


@dataclass
class SourceInfo:
    """Information about a fetched source."""

    name: str
    version: str | None = None
    url: str | None = None
    sha256: str | None = None
    fetched_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class FetchManifest:
    """Manifest tracking all fetched sources."""

    fetched_at: str
    domain: str
    generator_version: str
    sources: list[SourceInfo] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "fetched_at": self.fetched_at,
            "domain": self.domain,
            "generator_version": self.generator_version,
            "sources": [s.to_dict() for s in self.sources],
        }

    def save(self, path: Path) -> None:
        """Save manifest to JSON file."""
        path.write_text(json.dumps(self.to_dict(), indent=2))


def is_manifest_fresh(manifest_path: Path, max_age_hours: int = 24) -> bool:
    """Check if manifest exists and is less than max_age_hours old."""
    if not manifest_path.exists():
        return False

    try:
        manifest = json.loads(manifest_path.read_text())
        fetched_at = datetime.fromisoformat(manifest["fetched_at"])
        age = datetime.now(UTC) - fetched_at
        return age < timedelta(hours=max_age_hours)
    except (json.JSONDecodeError, KeyError, ValueError):
        return False


def fetch_http(
    url: str,
    output_dir: Path,
    name: str,
    filename: str | None = None,
    version_extractor: Callable[[dict], str] | None = None,
) -> SourceInfo:
    """
    Fetch a file from HTTP URL.

    Args:
        url: URL to fetch
        output_dir: Directory to save the file
        name: Name for this source
        filename: Optional filename (defaults to last part of URL)
        version_extractor: Optional function to extract version from JSON content

    Returns:
        SourceInfo with details about the fetched file
    """
    if filename is None:
        filename = url.split("/")[-1]

    output_path = output_dir / filename

    print(f"  Downloading {url}...")
    with urllib.request.urlopen(url) as response:
        content = response.read()

    # Calculate hash
    sha256 = hashlib.sha256(content).hexdigest()

    # Extract version if extractor provided
    version = None
    if version_extractor and filename.endswith(".json"):
        try:
            data = json.loads(content)
            version = version_extractor(data)
        except (json.JSONDecodeError, KeyError):
            pass

    # Write file
    output_path.write_bytes(content)
    print(f"  Saved to {output_path} ({len(content)} bytes)")

    return SourceInfo(
        name=name,
        url=url,
        sha256=sha256,
        version=version,
        fetched_at=datetime.now(UTC).isoformat(),
    )


def get_package_version(package_name: str) -> SourceInfo:
    """
    Get version info for an installed pip package.

    Args:
        package_name: Name of the package (e.g., "botocore")

    Returns:
        SourceInfo with package version
    """
    try:
        from importlib.metadata import version

        pkg_version = version(package_name)
        print(f"  {package_name} version: {pkg_version}")
        return SourceInfo(
            name=package_name,
            version=pkg_version,
        )
    except Exception as e:
        print(f"  WARNING: Could not get version for {package_name}: {e}")
        return SourceInfo(
            name=package_name,
            version="unknown",
        )
