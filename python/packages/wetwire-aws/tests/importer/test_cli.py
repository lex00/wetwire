"""Tests for CLI import command."""

import subprocess
import sys
from pathlib import Path

import pytest

TEMPLATES_DIR = Path(__file__).parent / "templates"


class TestImportCommand:
    """Test import CLI command."""

    def test_import_help(self):
        """Import subcommand shows help."""
        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "import", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "CloudFormation template" in result.stdout

    def test_import_missing_template(self, tmp_path):
        """Import fails gracefully for missing template."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "wetwire_aws.cli",
                "import",
                str(tmp_path / "nonexistent.yaml"),
                "-o",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "not found" in result.stderr

    def test_import_simple_bucket(self, tmp_path):
        """Import creates package from simple bucket template."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "wetwire_aws.cli",
                "import",
                str(TEMPLATES_DIR / "simple_bucket.yaml"),
                "-o",
                str(tmp_path),
                "-v",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # Check package structure created
        pkg_dir = tmp_path / "simple_bucket"
        assert pkg_dir.exists()
        assert (pkg_dir / "__init__.py").exists()
        assert (pkg_dir / "__main__.py").exists()
        assert (pkg_dir / "params.py").exists()

    def test_import_with_custom_name(self, tmp_path):
        """Import uses custom package name."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "wetwire_aws.cli",
                "import",
                str(TEMPLATES_DIR / "simple_bucket.yaml"),
                "-o",
                str(tmp_path),
                "-n",
                "my_custom_stack",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # Check custom package name used
        pkg_dir = tmp_path / "my_custom_stack"
        assert pkg_dir.exists()
        assert (pkg_dir / "__init__.py").exists()

    def test_import_single_file(self, tmp_path):
        """Import --single-file creates single Python file."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "wetwire_aws.cli",
                "import",
                str(TEMPLATES_DIR / "simple_bucket.yaml"),
                "-o",
                str(tmp_path),
                "--single-file",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # Check single file created
        single_file = tmp_path / "simple_bucket.py"
        assert single_file.exists()

        # Verify it's valid Python
        content = single_file.read_text()
        compile(content, str(single_file), "exec")

    def test_import_json_template(self, tmp_path):
        """Import handles JSON templates."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "wetwire_aws.cli",
                "import",
                str(TEMPLATES_DIR / "simple_bucket.json"),
                "-o",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # Check package created
        pkg_dir = tmp_path / "simple_bucket"
        assert pkg_dir.exists()

    def test_import_no_overwrite_by_default(self, tmp_path):
        """Import does not overwrite existing files without --force."""
        # First import
        subprocess.run(
            [
                sys.executable,
                "-m",
                "wetwire_aws.cli",
                "import",
                str(TEMPLATES_DIR / "simple_bucket.yaml"),
                "-o",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )

        # Modify a file
        init_file = tmp_path / "simple_bucket" / "__init__.py"
        original_content = init_file.read_text()
        init_file.write_text("# Modified\n" + original_content)

        # Second import without --force
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "wetwire_aws.cli",
                "import",
                str(TEMPLATES_DIR / "simple_bucket.yaml"),
                "-o",
                str(tmp_path),
                "-v",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Skipping" in result.stderr

        # File should not be overwritten
        assert init_file.read_text().startswith("# Modified")

    def test_import_force_overwrites(self, tmp_path):
        """Import --force overwrites existing files."""
        # First import
        subprocess.run(
            [
                sys.executable,
                "-m",
                "wetwire_aws.cli",
                "import",
                str(TEMPLATES_DIR / "simple_bucket.yaml"),
                "-o",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )

        # Modify a file
        init_file = tmp_path / "simple_bucket" / "__init__.py"
        init_file.write_text("# Modified\n")

        # Second import with --force
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "wetwire_aws.cli",
                "import",
                str(TEMPLATES_DIR / "simple_bucket.yaml"),
                "-o",
                str(tmp_path),
                "--force",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # File should be overwritten
        assert not init_file.read_text().startswith("# Modified")

    def test_import_intrinsics_template(self, tmp_path):
        """Import handles templates with intrinsic functions."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "wetwire_aws.cli",
                "import",
                str(TEMPLATES_DIR / "intrinsics.yaml"),
                "-o",
                str(tmp_path),
                "--single-file",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # Check file created and is valid Python
        single_file = tmp_path / "intrinsics.py"
        assert single_file.exists()
        content = single_file.read_text()
        compile(content, str(single_file), "exec")

        # Check for intrinsic functions
        assert "Sub(" in content
        assert "Join(" in content
        assert "If(" in content
