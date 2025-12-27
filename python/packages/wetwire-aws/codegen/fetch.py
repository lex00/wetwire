"""
Stage 1: Fetch source materials.

Downloads the CloudFormation spec and records botocore version info.
"""

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import requests

from codegen.config import GENERATOR_VERSION, SOURCES, SPECS_DIR


def fetch_http(source: dict, specs_dir: Path) -> dict:
    """Fetch a file via HTTP."""
    url = source["url"]
    filename = source.get("filename", url.split("/")[-1])
    local_path = specs_dir / filename

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
    print(f"  Saved to {local_path}")

    # Extract version if extractor provided
    version = None
    if "extract_version" in source:
        try:
            data = json.loads(content)
            version = source["extract_version"](data)
            print(f"  Version: {version}")
        except (json.JSONDecodeError, KeyError):
            pass

    return {
        "name": source["name"],
        "type": "http",
        "url": url,
        "version": version,
        "sha256": hashlib.sha256(content).hexdigest(),
        "local_path": filename,
        "fetched_at": datetime.now(UTC).isoformat(),
    }


def fetch_pip_info(source: dict) -> dict:
    """Get version info for an installed pip package."""
    package = source["package"]

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

    print(f"  Version: {version}")

    return {
        "name": source["name"],
        "type": "pip",
        "package": package,
        "version": version,
        "fetched_at": datetime.now(UTC).isoformat(),
    }


def should_fetch(specs_dir: Path, max_age_hours: int = 24) -> bool:
    """Check if we need to fetch again."""
    manifest_path = specs_dir / "manifest.json"

    if not manifest_path.exists():
        return True

    try:
        manifest = json.loads(manifest_path.read_text())
        fetched_at_str = manifest.get("fetched_at", "")
        if not fetched_at_str:
            return True

        # Parse ISO format timestamp
        fetched_at = datetime.fromisoformat(fetched_at_str.replace("Z", "+00:00"))
        age = datetime.now(UTC) - fetched_at

        return age.total_seconds() > max_age_hours * 3600
    except (json.JSONDecodeError, ValueError):
        return True


def fetch(force: bool = False) -> dict:
    """
    Run the fetch stage.

    Downloads source materials and writes manifest.json.
    """
    print("Stage 1: Fetch")
    print("=" * 40)

    # Ensure specs directory exists
    SPECS_DIR.mkdir(parents=True, exist_ok=True)

    # Check freshness
    if not force and not should_fetch(SPECS_DIR):
        print("Sources are fresh (< 24h old). Use --force to re-fetch.")
        manifest_path = SPECS_DIR / "manifest.json"
        return json.loads(manifest_path.read_text())

    # Fetch each source
    source_results = []
    for source in SOURCES:
        print(f"\nFetching {source['name']}...")
        try:
            if source["type"] == "http":
                result = fetch_http(source, SPECS_DIR)
            elif source["type"] == "pip":
                result = fetch_pip_info(source)
            else:
                raise ValueError(f"Unknown source type: {source['type']}")
            source_results.append(result)
        except Exception as e:
            print(f"  ERROR: {e}")
            raise

    # Write manifest
    manifest = {
        "fetched_at": datetime.now(UTC).isoformat(),
        "domain": "aws",
        "generator_version": GENERATOR_VERSION,
        "sources": source_results,
        "status": "success",
    }

    manifest_path = SPECS_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest written to {manifest_path}")

    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Fetch CloudFormation spec and botocore info"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force re-fetch even if fresh"
    )
    args = parser.parse_args()

    try:
        fetch(force=args.force)
        print("\nFetch completed successfully!")
    except Exception as e:
        print(f"\nFetch failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
