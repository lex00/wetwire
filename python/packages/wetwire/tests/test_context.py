"""Tests for Context class."""

from wetwire import ENVIRONMENT, PROJECT, Context


class TestContext:
    """Tests for Context class."""

    def test_default_context(self):
        """Test default context values."""
        ctx = Context()
        assert ctx.project == ""
        assert ctx.environment == ""

    def test_context_with_values(self):
        """Test context with custom values."""
        ctx = Context(project="myapp", environment="prod")
        assert ctx.project == "myapp"
        assert ctx.environment == "prod"

    def test_get_existing_value(self):
        """Test getting an existing context value."""
        ctx = Context(project="myapp")
        assert ctx.get("project") == "myapp"

    def test_get_missing_value_with_default(self):
        """Test getting missing value returns default."""
        ctx = Context()
        assert ctx.get("missing", "fallback") == "fallback"

    def test_get_missing_value_without_default(self):
        """Test getting missing value returns None by default."""
        ctx = Context()
        assert ctx.get("missing") is None


class TestContextSubclass:
    """Tests for subclassing Context."""

    def test_custom_context(self):
        """Test custom context with additional fields."""
        from dataclasses import dataclass

        @dataclass
        class AWSContext(Context):
            account_id: str = ""
            region: str = ""

        ctx = AWSContext(
            project="myapp",
            environment="prod",
            account_id="123456789",
            region="us-east-1",
        )

        assert ctx.project == "myapp"
        assert ctx.account_id == "123456789"
        assert ctx.get("region") == "us-east-1"


class TestContextRefs:
    """Tests for pre-built context references."""

    def test_project_ref_exists(self):
        """Test PROJECT constant exists."""
        assert PROJECT is not None

    def test_environment_ref_exists(self):
        """Test ENVIRONMENT constant exists."""
        assert ENVIRONMENT is not None
