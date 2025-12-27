"""Tests for CLI utilities."""

import argparse
from unittest.mock import patch

import pytest

from wetwire import (
    add_common_args,
    create_list_command,
    create_validate_command,
    discover_resources,
    registry,
    wetwire,
)


class TestDiscoverResources:
    """Tests for discover_resources()."""

    def test_discover_resources_counts_registrations(self):
        """Test that discover_resources returns the count of new resources."""

        # Register a resource before discovery
        @wetwire
        class ExistingResource:
            name: str = "existing"

        # Mock importing a module that registers resources
        with patch("wetwire.cli.importlib.import_module") as mock_import:

            def side_effect(module_path):
                # Simulate resource registration during import
                @wetwire
                class NewResource:
                    name: str = "new"

            mock_import.side_effect = side_effect

            count = discover_resources("fake.module", registry)
            assert count == 1
            mock_import.assert_called_once_with("fake.module")

    def test_discover_resources_verbose(self, capsys):
        """Test verbose output."""
        with patch("wetwire.cli.importlib.import_module"):
            discover_resources("fake.module", registry, verbose=True)
            captured = capsys.readouterr()
            assert "Discovered" in captured.err
            assert "fake.module" in captured.err


class TestAddCommonArgs:
    """Tests for add_common_args()."""

    def test_adds_module_argument(self):
        """Test that --module/-m is added."""
        parser = argparse.ArgumentParser()
        add_common_args(parser)

        args = parser.parse_args(["--module", "myapp.infra"])
        assert args.modules == ["myapp.infra"]

    def test_adds_scope_argument(self):
        """Test that --scope/-s is added."""
        parser = argparse.ArgumentParser()
        add_common_args(parser)

        args = parser.parse_args(["--scope", "myapp.prod"])
        assert args.scope == "myapp.prod"

    def test_adds_verbose_argument(self):
        """Test that --verbose/-v is added."""
        parser = argparse.ArgumentParser()
        add_common_args(parser)

        args = parser.parse_args(["--verbose"])
        assert args.verbose is True

    def test_module_is_repeatable(self):
        """Test that --module can be specified multiple times."""
        parser = argparse.ArgumentParser()
        add_common_args(parser)

        args = parser.parse_args(["-m", "mod1", "-m", "mod2"])
        assert args.modules == ["mod1", "mod2"]


class TestCreateListCommand:
    """Tests for create_list_command()."""

    def test_list_command_lists_resources(self, capsys):
        """Test that list command outputs registered resources."""

        @wetwire
        class MyResource:
            name: str = "test"

        def get_type(cls):
            return "TestType"

        list_cmd = create_list_command(registry, get_type)

        args = argparse.Namespace(modules=None, scope=None, verbose=False)
        list_cmd(args)

        captured = capsys.readouterr()
        assert "MyResource" in captured.out
        assert "TestType" in captured.out

    def test_list_command_handles_empty_registry(self, capsys):
        """Test that list command handles no resources."""

        def get_type(cls):
            return "TestType"

        list_cmd = create_list_command(registry, get_type)

        args = argparse.Namespace(modules=None, scope=None, verbose=False)
        list_cmd(args)

        captured = capsys.readouterr()
        assert "No resources registered" in captured.err


class TestCreateValidateCommand:
    """Tests for create_validate_command()."""

    def test_validate_command_passes_with_valid_refs(self, capsys):
        """Test that validation passes when all references exist."""

        @wetwire
        class ResourceA:
            name: str = "a"

        @wetwire
        class ResourceB:
            name: str = "b"

        validate_cmd = create_validate_command(registry)

        args = argparse.Namespace(modules=None, scope=None, verbose=False)
        validate_cmd(args)

        captured = capsys.readouterr()
        assert "Validation passed" in captured.out

    def test_validate_command_exits_on_empty_registry(self):
        """Test that validation exits when no resources registered."""
        validate_cmd = create_validate_command(registry)

        args = argparse.Namespace(modules=None, scope=None, verbose=False)

        with pytest.raises(SystemExit) as exc_info:
            validate_cmd(args)
        assert exc_info.value.code == 1
