"""Tests for computed field support."""

from wetwire.computed import ComputedDescriptor, computed


class TestComputedDescriptor:
    """Tests for ComputedDescriptor class (standalone, without @wetwire)."""

    def test_descriptor_basic(self):
        """Test basic computed descriptor."""

        class MyClass:
            first = "hello"
            second = "world"

            @computed
            def combined(self) -> str:
                return f"{self.first}-{self.second}"

        instance = MyClass()
        assert instance.combined == "hello-world"

    def test_descriptor_recomputes_on_access(self):
        """Test computed field recomputes each time."""

        class Counter:
            def __init__(self):
                self.count = 0

            @computed
            def value(self) -> int:
                self.count += 1
                return self.count

        instance = Counter()
        # Each access should increment
        assert instance.value == 1
        assert instance.value == 2
        assert instance.value == 3

    def test_descriptor_on_class_access(self):
        """Test accessing computed on class returns descriptor."""

        class MyClass:
            @computed
            def value(self) -> str:
                return "test"

        # Accessing on class should return the descriptor
        descriptor = MyClass.value
        assert isinstance(descriptor, ComputedDescriptor)
        assert hasattr(descriptor, "func")

    def test_descriptor_repr(self):
        """Test descriptor string representation."""

        class MyClass:
            @computed
            def my_field(self) -> str:
                return "test"

        descriptor = MyClass.my_field
        assert "computed" in repr(descriptor)
        assert "my_field" in repr(descriptor)

    def test_descriptor_with_different_instances(self):
        """Test computed field respects instance values."""

        class Named:
            def __init__(self, prefix="default"):
                self.prefix = prefix

            @computed
            def full_name(self) -> str:
                return f"{self.prefix}-resource"

        instance1 = Named()
        instance2 = Named(prefix="custom")

        assert instance1.full_name == "default-resource"
        assert instance2.full_name == "custom-resource"

    def test_descriptor_with_complex_logic(self):
        """Test computed with complex logic."""

        class Config:
            def __init__(self, environment="prod", base_size=10):
                self.environment = environment
                self.base_size = base_size

            @computed
            def instance_size(self) -> int:
                multiplier = 4 if self.environment == "prod" else 1
                return self.base_size * multiplier

        prod = Config()
        dev = Config(environment="dev")

        assert prod.instance_size == 40
        assert dev.instance_size == 10

    def test_set_name_called(self):
        """Test __set_name__ is called correctly."""

        class MyClass:
            @computed
            def my_prop(self) -> str:
                return "test"

        descriptor = MyClass.my_prop
        assert descriptor.name == "my_prop"
