"""Tests for lint CLI command."""

import subprocess
import sys
from pathlib import Path

import pytest


class TestLintCommand:
    """Test lint CLI command."""

    def test_lint_help(self):
        """Lint subcommand shows help."""
        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "lint", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "lint" in result.stdout
        assert "--fix" in result.stdout

    def test_lint_missing_path(self, tmp_path):
        """Lint fails gracefully for missing path."""
        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "lint",
             str(tmp_path / "nonexistent")],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "not found" in result.stderr

    def test_lint_no_issues(self, tmp_path):
        """Lint returns 0 when no issues found."""
        test_file = tmp_path / "clean.py"
        test_file.write_text('"""Clean code."""\nx = 1\n')

        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "lint", str(test_file)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_lint_detects_issues(self, tmp_path):
        """Lint detects and reports issues."""
        test_file = tmp_path / "with_issues.py"
        test_file.write_text('sse_algorithm = "AES256"\n')

        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "lint", str(test_file)],
            capture_output=True,
            text=True,
        )
        # Should have non-zero exit code when issues found
        assert result.returncode != 0
        assert "WAW003" in result.stdout
        assert "ServerSideEncryption" in result.stdout

    def test_lint_directory(self, tmp_path):
        """Lint scans all Python files in directory."""
        (tmp_path / "a.py").write_text('"""A."""\n')
        (tmp_path / "b.py").write_text('"""B."""\n')
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "c.py").write_text('"""C."""\n')

        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "lint", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_lint_with_fix(self, tmp_path):
        """Lint --fix modifies files in place."""
        test_file = tmp_path / "fixable.py"
        test_file.write_text('sse_algorithm = "AES256"\n')

        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "lint", str(test_file), "--fix"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Fixed" in result.stdout

        # Verify the file was modified
        content = test_file.read_text()
        assert "ServerSideEncryption.AES256" in content
        assert '"AES256"' not in content

    def test_lint_fix_uses_module_qualified_names(self, tmp_path):
        """Lint --fix uses module-qualified enum names (no import needed)."""
        test_file = tmp_path / "needs_fix.py"
        test_file.write_text('sse_algorithm = "AES256"\n')

        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "lint", str(test_file), "--fix"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        content = test_file.read_text()
        # Should use module-qualified name, not import statement
        assert "s3.ServerSideEncryption.AES256" in content
        # No import statement should be added (setup_resources provides s3 module)
        assert "from wetwire_aws.resources.s3 import" not in content

    def test_lint_verbose(self, tmp_path):
        """Lint --verbose shows extra output."""
        test_file = tmp_path / "clean.py"
        test_file.write_text('"""Clean code."""\n')

        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "lint",
             str(test_file), "--verbose"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "No issues found" in result.stderr
