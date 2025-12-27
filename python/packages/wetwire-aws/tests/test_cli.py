"""Tests for CLI functionality."""

import subprocess
import sys


class TestCLI:
    """Test CLI commands."""

    def test_help(self):
        """CLI shows help message."""
        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Generate CloudFormation templates" in result.stdout

    def test_version(self):
        """CLI shows version."""
        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "0.1.0" in result.stdout

    def test_build_no_resources(self):
        """Build fails gracefully when no resources registered."""
        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "build"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "No resources registered" in result.stderr

    def test_list_no_resources(self):
        """List shows message when no resources registered."""
        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "list"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "No resources registered" in result.stderr

    def test_validate_no_resources(self):
        """Validate fails when no resources registered."""
        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "validate"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "No resources registered" in result.stderr
