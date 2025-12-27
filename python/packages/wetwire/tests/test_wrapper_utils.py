"""Tests for wrapper utilities."""

from dataclasses import dataclass

from wetwire._internal.wrapper_utils import (
    get_logical_id,
    get_wrapped_type,
    is_wrapper_class,
)


class MockResource:
    """Mock resource type for testing."""

    pass


class TestIsWrapperClass:
    """Tests for is_wrapper_class()."""

    def test_with_resource_field(self):
        """Test class with resource field is detected."""

        @dataclass
        class MyWrapper:
            resource: MockResource

        assert is_wrapper_class(MyWrapper) is True

    def test_without_resource_field(self):
        """Test class without resource field is not detected."""

        @dataclass
        class NotWrapper:
            name: str = "test"

        assert is_wrapper_class(NotWrapper) is False

    def test_non_dataclass(self):
        """Test non-dataclass is not detected."""

        class PlainClass:
            resource: MockResource

        assert is_wrapper_class(PlainClass) is False

    def test_with_string_annotation(self):
        """Test class with string annotation (forward reference)."""

        @dataclass
        class MyWrapper:
            resource: "MockResource"

        assert is_wrapper_class(MyWrapper) is True


class TestGetWrappedType:
    """Tests for get_wrapped_type()."""

    def test_returns_resource_type(self):
        """Test returns the resource type."""

        @dataclass
        class MyWrapper:
            resource: MockResource

        result = get_wrapped_type(MyWrapper)
        assert result is MockResource

    def test_non_wrapper_returns_none(self):
        """Test non-wrapper class returns None."""

        @dataclass
        class NotWrapper:
            name: str = "test"

        assert get_wrapped_type(NotWrapper) is None

    def test_with_string_annotation(self):
        """Test with string annotation resolves type."""

        @dataclass
        class MyWrapper:
            resource: "MockResource"

        result = get_wrapped_type(MyWrapper)
        assert result is MockResource

    def test_missing_resource_annotation(self):
        """Test class with no resource annotation."""

        @dataclass
        class NoResource:
            other: str = "test"

        assert get_wrapped_type(NoResource) is None


class TestGetLogicalId:
    """Tests for get_logical_id()."""

    def test_default_uses_class_name(self):
        """Test default logical ID is class name."""

        @dataclass
        class MyResource:
            resource: MockResource

        assert get_logical_id(MyResource) == "MyResource"

    def test_custom_logical_id(self):
        """Test custom _logical_id is used."""

        @dataclass
        class MyResource:
            _logical_id = "CustomLogicalId"
            resource: MockResource

        assert get_logical_id(MyResource) == "CustomLogicalId"

    def test_with_plain_class(self):
        """Test works with non-dataclass too."""

        class PlainClass:
            pass

        assert get_logical_id(PlainClass) == "PlainClass"
