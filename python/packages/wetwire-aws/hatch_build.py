"""
Custom Hatch build hook for wetwire-aws.

Runs the codegen pipeline to generate AWS CloudFormation resource classes
during package build. This enables the repository to remain clean (no
generated code committed) while still producing wheels with all resources.

Usage:
    hatch build                      # Generates resources, then builds
    WETWIRE_SKIP_CODEGEN=1 hatch build  # Skip codegen if resources exist
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CodegenBuildHook(BuildHookInterface):
    """Build hook that runs codegen before packaging."""

    PLUGIN_NAME = "codegen"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Run codegen before the build starts."""
        if self.target_name not in ("wheel", "sdist"):
            return

        resources_dir = Path(self.root) / "src" / "wetwire_aws" / "resources"
        init_file = resources_dir / "__init__.py"

        # Skip if WETWIRE_SKIP_CODEGEN is set and resources exist
        if os.environ.get("WETWIRE_SKIP_CODEGEN") and init_file.exists():
            self.app.display_info("Skipping codegen (WETWIRE_SKIP_CODEGEN set)")
            return

        # Skip if resources already exist (for sdist installs)
        if init_file.exists() and self._resources_look_complete(resources_dir):
            self.app.display_info("Resources already exist, skipping codegen")
            return

        self.app.display_info("Running wetwire-aws codegen pipeline...")
        self._run_codegen()

    def _resources_look_complete(self, resources_dir: Path) -> bool:
        """Check if resources directory looks complete (has multiple service dirs)."""
        if not resources_dir.exists():
            return False
        # Check for at least 10 service directories (should have 260+)
        service_dirs = [d for d in resources_dir.iterdir() if d.is_dir()]
        return len(service_dirs) >= 10

    def _run_codegen(self) -> None:
        """Run the four-stage codegen pipeline."""
        # Stage 1: Fetch CloudFormation spec
        self.app.display_info("  Stage 1/4: Fetching CloudFormation spec...")
        self._run_python_module("codegen.fetch", "--force")

        # Stage 2: Parse spec to intermediate format
        self.app.display_info("  Stage 2/4: Parsing spec...")
        self._run_python_module("codegen.parse")

        # Stage 3: Extract enums from botocore
        self.app.display_info("  Stage 3/4: Extracting enums from botocore...")
        self._run_python_module("codegen.extract_enums")

        # Stage 4: Generate Python classes
        self.app.display_info("  Stage 4/4: Generating Python classes...")
        self._run_python_module("codegen.generate")

        self.app.display_info("Codegen complete!")

    def _run_python_module(self, module: str, *args: str) -> None:
        """Run a Python module as a subprocess."""
        cmd = [sys.executable, "-m", module, *args]
        result = subprocess.run(
            cmd,
            cwd=self.root,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.app.display_error(f"Codegen failed: {result.stderr}")
            raise RuntimeError(f"Codegen module {module} failed: {result.stderr}")
