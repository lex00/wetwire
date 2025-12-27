"""
Stage 1: Fetch source materials.

Downloads the CloudFormation spec and records botocore version info.
"""

import argparse
import json
import sys
from datetime import UTC, datetime

from codegen.config import GENERATOR_VERSION, SOURCES, SPECS_DIR
from wetwire.codegen.fetcher import (
    FetchManifest,
    fetch_http as _fetch_http,
    get_package_version,
    is_manifest_fresh,
)


def fetch(force: bool = False) -> dict:
    """
    Run the fetch stage.

    Downloads source materials and writes manifest.json.
    """
    print("Stage 1: Fetch")
    print("=" * 40)

    # Ensure specs directory exists
    SPECS_DIR.mkdir(parents=True, exist_ok=True)

    manifest_path = SPECS_DIR / "manifest.json"

    # Check freshness
    if not force and is_manifest_fresh(manifest_path):
        print("Sources are fresh (< 24h old). Use --force to re-fetch.")
        return json.loads(manifest_path.read_text())

    # Fetch each source
    manifest = FetchManifest(
        fetched_at=datetime.now(UTC).isoformat(),
        domain="aws",
        generator_version=GENERATOR_VERSION,
    )

    for source in SOURCES:
        print(f"\nFetching {source['name']}...")
        try:
            if source["type"] == "http":
                result = _fetch_http(
                    url=source["url"],
                    output_dir=SPECS_DIR,
                    name=source["name"],
                    filename=source.get("filename"),
                    version_extractor=source.get("extract_version"),
                )
            elif source["type"] == "pip":
                result = get_package_version(source["package"])
                result.name = source["name"]  # Use source name, not package name
            else:
                raise ValueError(f"Unknown source type: {source['type']}")
            manifest.sources.append(result)
        except Exception as e:
            print(f"  ERROR: {e}")
            raise

    # Write manifest
    manifest.save(manifest_path)
    print(f"\nManifest written to {manifest_path}")

    return manifest.to_dict()


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
