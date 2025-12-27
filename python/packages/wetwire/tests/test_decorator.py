"""Tests for the @wetwire decorator."""

from dataclasses import is_dataclass

from wetwire import registry, wetwire


class MockResource:
    """Mock resource type for testing."""

    pass


class TestWetwireDecorator:
    """Tests for the @wetwire decorator."""

    def test_creates_dataclass(self):
        """Decorator should create a dataclass."""

        @wetwire
        class MyResource:
            resource: MockResource
            name: str = "test"

        assert is_dataclass(MyResource)

    def test_can_instantiate_without_args(self):
        """Decorated class should be instantiable without arguments."""

        @wetwire
        class MyResource:
            resource: MockResource
            name: str = "test"

        instance = MyResource()
        assert instance.name == "test"
        assert instance.resource is None

    def test_registers_with_registry(self):
        """Decorator should register the class."""

        @wetwire
        class MyResource:
            resource: MockResource

        assert "MyResource" in registry
        assert len(registry) == 1

    def test_register_false_skips_registration(self):
        """register=False should skip registration."""

        @wetwire(register=False)
        class MyResource:
            resource: MockResource

        assert "MyResource" not in registry
        assert len(registry) == 0

    def test_handles_mutable_defaults(self):
        """Decorator should handle mutable defaults correctly."""

        @wetwire
        class MyResource:
            resource: MockResource
            tags: list = ["default"]
            config: dict = {"key": "value"}

        r1 = MyResource()
        r2 = MyResource()

        # Should be separate instances
        assert r1.tags is not r2.tags
        assert r1.config is not r2.config

    def test_preserves_field_values(self):
        """Decorator should preserve field default values."""

        @wetwire
        class MyResource:
            resource: MockResource
            name: str = "default-name"
            count: int = 42
            enabled: bool = True

        instance = MyResource()
        assert instance.name == "default-name"
        assert instance.count == 42
        assert instance.enabled is True

    def test_allows_field_override(self):
        """Fields should be overridable at instantiation."""

        @wetwire
        class MyResource:
            resource: MockResource
            name: str = "default"

        instance = MyResource(name="custom")
        assert instance.name == "custom"

    def test_decorator_with_parens(self):
        """Decorator should work with parentheses."""

        @wetwire()
        class MyResource:
            resource: MockResource

        assert is_dataclass(MyResource)
        assert "MyResource" in registry

    def test_decorator_without_parens(self):
        """Decorator should work without parentheses."""

        @wetwire
        class MyResource:
            resource: MockResource

        assert is_dataclass(MyResource)
        assert "MyResource" in registry
