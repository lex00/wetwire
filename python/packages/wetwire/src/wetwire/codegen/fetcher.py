"""
Source fetching utilities for code generation.

Provides utilities for downloading specification files and
checking package versions.
"""

import gzip
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

# Import requests lazily to avoid requiring it at import time
_requests = None


def _get_requests():
    """Lazily import requests."""
    global _requests
    if _requests is None:
        try:
            import requests

            _requests = requests
        except ImportError as e:
            raise ImportError(
                "requests is required for fetching. "
                "Install with: pip install wetwire[codegen]"
            ) from e
    return _requests


@dataclass
class SourceResult:
    """Result of fetching a single source."""

    name: str
    type: str  # "http" or "pip"
    version: str | None = None
    sha256: str | None = None
    local_path: str | None = None
    url: str | None = None
    package: str | None = None
    fetched_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result: dict[str, Any] = {
            "name": self.name,
            "type": self.type,
            "fetched_at": self.fetched_at,
        }
        if self.version:
            result["version"] = self.version
        if self.sha256:
            result["sha256"] = self.sha256
        if self.local_path:
            result["local_path"] = self.local_path
        if self.url:
            result["url"] = self.url
        if self.package:
            result["package"] = self.package
        return result


@dataclass
class FetchManifest:
    """Manifest of fetched sources."""

    fetched_at: str
    domain: str
    generator_version: str
    sources: list[SourceResult] = field(default_factory=list)
    status: str = "success"

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "fetched_at": self.fetched_at,
            "domain": self.domain,
            "generator_version": self.generator_version,
            "sources": [s.to_dict() for s in self.sources],
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FetchManifest":
        """Load from JSON dict."""
        manifest = cls(
            fetched_at=data.get("fetched_at", ""),
            domain=data.get("domain", ""),
            generator_version=data.get("generator_version", ""),
            status=data.get("status", "success"),
        )
        for s in data.get("sources", []):
            manifest.sources.append(
                SourceResult(
                    name=s["name"],
                    type=s["type"],
                    version=s.get("version"),
                    sha256=s.get("sha256"),
                    local_path=s.get("local_path"),
                    url=s.get("url"),
                    package=s.get("package"),
                    fetched_at=s.get("fetched_at", ""),
                )
            )
        return manifest

    def save(self, path: Path) -> None:
        """Save manifest to a JSON file."""
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> "FetchManifest":
        """Load manifest from a JSON file."""
        return cls.from_dict(json.loads(path.read_text()))


def fetch_http(
    url: str,
    output_dir: Path,
    name: str,
    filename: str | None = None,
    version_extractor: Callable[[dict[str, Any]], str | None] | None = None,
    verbose: bool = True,
) -> SourceResult:
    """
    Fetch a file via HTTP.

    Handles gzip-compressed responses automatically.

    Args:
        url: The URL to fetch
        output_dir: Directory to save the file
        name: Name for this source (used in manifest)
        filename: Output filename (defaults to last URL segment)
        version_extractor: Optional function to extract version from JSON content
        verbose: Whether to print progress messages

    Returns:
        SourceResult with fetch details
    """
    requests = _get_requests()

    if filename is None:
        filename = url.split("/")[-1]

    local_path = output_dir / filename

    if verbose:
        print(f"  Fetching {url}...")

    response = requests.get(url, timeout=60)
    response.raise_for_status()

    content = response.content

    # Decompress if gzip
    if (
        "gzip" in url
        or url.endswith(".gz")
        or response.headers.get("Content-Encoding") == "gzip"
    ):
        try:
            content = gzip.decompress(content)
        except gzip.BadGzipFile:
            pass  # Not actually gzipped

    local_path.write_bytes(content)
    if verbose:
        print(f"  Saved to {local_path}")

    # Extract version if extractor provided
    version = None
    if version_extractor is not None:
        try:
            data = json.loads(content)
            version = version_extractor(data)
            if verbose and version:
                print(f"  Version: {version}")
        except (json.JSONDecodeError, KeyError):
            pass

    return SourceResult(
        name=name,
        type="http",
        url=url,
        version=version,
        sha256=hashlib.sha256(content).hexdigest(),
        local_path=filename,
        fetched_at=datetime.now(UTC).isoformat(),
    )


def get_package_version(package: str, verbose: bool = True) -> SourceResult:
    """
    Get version info for an installed pip package.

    Args:
        package: The package name to check
        verbose: Whether to print progress messages

    Returns:
        SourceResult with version info
    """
    if verbose:
        print(f"  Checking {package} version...")

    version = None

    # Try importlib.metadata first (works with uv and pip)
    try:
        from importlib.metadata import version as get_version

        version = get_version(package)
    except ImportError:
        pass
    except Exception:
        pass

    # Fall back to pip show if importlib.metadata failed
    if version is None:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.startswith("Version:"):
                    version = line.split(":", 1)[1].strip()
                    break

    if version is None:
        raise RuntimeError(
            f"Package {package} not installed. Install with: pip install {package}"
        )

    if verbose:
        print(f"  Version: {version}")

    return SourceResult(
        name=package,
        type="pip",
        package=package,
        version=version,
        fetched_at=datetime.now(UTC).isoformat(),
    )


def is_manifest_fresh(manifest_path: Path, max_age_hours: int = 24) -> bool:
    """
    Check if a manifest is fresh (less than max_age_hours old).

    Args:
        manifest_path: Path to the manifest.json file
        max_age_hours: Maximum age in hours to consider fresh

    Returns:
        True if the manifest exists and is fresh, False otherwise
    """
    if not manifest_path.exists():
        return False

    try:
        manifest = json.loads(manifest_path.read_text())
        fetched_at_str = manifest.get("fetched_at", "")
        if not fetched_at_str:
            return False

        # Parse ISO format timestamp
        fetched_at = datetime.fromisoformat(fetched_at_str.replace("Z", "+00:00"))
        age = datetime.now(UTC) - fetched_at

        return age.total_seconds() <= max_age_hours * 3600
    except (json.JSONDecodeError, ValueError):
        return False
