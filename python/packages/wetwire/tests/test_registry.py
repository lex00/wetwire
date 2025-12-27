"""Tests for the ResourceRegistry."""

from wetwire import ResourceRegistry, registry, wetwire


class MockResource:
    """Mock resource type for testing."""

    pass


class AnotherResource:
    """Another mock resource type."""

    pass


class TestResourceRegistry:
    """Tests for ResourceRegistry."""

    def test_register_and_get_by_name(self):
        """Should register and retrieve by name."""

        @wetwire
        class MyResource:
            resource: MockResource

        assert registry.get_by_name("MyResource") is MyResource
        assert registry.get_by_name("NonExistent") is None

    def test_get_all(self):
        """Should get all registered resources."""

        @wetwire
        class Resource1:
            resource: MockResource

        @wetwire
        class Resource2:
            resource: MockResource

        all_resources = registry.get_all()
        assert len(all_resources) == 2
        assert Resource1 in all_resources
        assert Resource2 in all_resources

    def test_get_by_type(self):
        """Should get resources by their wrapped type."""

        @wetwire
        class MyMock:
            resource: MockResource

        @wetwire
        class MyAnother:
            resource: AnotherResource

        mock_resources = registry.get_by_type(MockResource)
        assert len(mock_resources) == 1
        assert MyMock in mock_resources

        another_resources = registry.get_by_type(AnotherResource)
        assert len(another_resources) == 1
        assert MyAnother in another_resources

    def test_contains(self):
        """Should support 'in' operator."""

        @wetwire
        class MyResource:
            resource: MockResource

        assert "MyResource" in registry
        assert "NonExistent" not in registry

    def test_len(self):
        """Should support len()."""
        assert len(registry) == 0

        @wetwire
        class Resource1:
            resource: MockResource

        assert len(registry) == 1

        @wetwire
        class Resource2:
            resource: MockResource

        assert len(registry) == 2

    def test_clear(self):
        """Should clear all registrations."""

        @wetwire
        class MyResource:
            resource: MockResource

        assert len(registry) == 1
        registry.clear()
        assert len(registry) == 0

    def test_scope_package_filter(self):
        """Should filter by package scope."""
        # Create a new registry for this test
        reg = ResourceRegistry()

        # Manually register with module names
        class Resource1:
            __module__ = "myproject.aws.resources"
            resource: MockResource

        class Resource2:
            __module__ = "myproject.gcp.resources"
            resource: MockResource

        class Resource3:
            __module__ = "otherproject.resources"
            resource: MockResource

        reg.register(Resource1)
        reg.register(Resource2)
        reg.register(Resource3)

        # Filter by scope
        myproject = reg.get_all(scope_package="myproject")
        assert len(myproject) == 2

        aws_only = reg.get_all(scope_package="myproject.aws")
        assert len(aws_only) == 1

        other = reg.get_all(scope_package="otherproject")
        assert len(other) == 1

    def test_repr(self):
        """Should have a useful repr."""

        @wetwire
        class MyResource:
            resource: MockResource

        assert "1 resources" in repr(registry)
