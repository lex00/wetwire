"""Tests for Provider abstract class."""

from typing import Any

from wetwire import Provider, Template, wetwire


class MockProvider(Provider):
    """Mock provider for testing."""

    name = "mock"

    def serialize_ref(self, source: type[Any], target: type[Any]) -> Any:
        return {"MockRef": target.__name__}

    def serialize_attr(
        self, source: type[Any], target: type[Any], attr_name: str
    ) -> Any:
        return {"MockGetAtt": [target.__name__, attr_name]}

    def serialize_resource(self, resource: Any) -> dict[str, Any]:
        return {
            "Type": "Mock::Resource",
            "Properties": {"name": getattr(resource, "name", "unknown")},
        }


class TestProvider:
    """Tests for Provider abstract class."""

    def test_provider_name(self):
        """Test provider has a name."""
        provider = MockProvider()
        assert provider.name == "mock"

    def test_serialize_ref(self):
        """Test serialize_ref method."""

        @wetwire
        class TargetResource:
            name: str = "target"

        provider = MockProvider()
        result = provider.serialize_ref(None, TargetResource)
        assert result == {"MockRef": "TargetResource"}

    def test_serialize_attr(self):
        """Test serialize_attr method."""

        @wetwire
        class TargetResource:
            name: str = "target"

        provider = MockProvider()
        result = provider.serialize_attr(None, TargetResource, "Arn")
        assert result == {"MockGetAtt": ["TargetResource", "Arn"]}

    def test_serialize_resource(self):
        """Test serialize_resource method."""

        @wetwire
        class MyResource:
            name: str = "test-resource"

        provider = MockProvider()
        instance = MyResource()
        result = provider.serialize_resource(instance)
        assert result["Type"] == "Mock::Resource"
        assert result["Properties"]["name"] == "test-resource"

    def test_get_logical_id_default(self):
        """Test get_logical_id returns class name by default."""

        @wetwire
        class MyResource:
            name: str = "test"

        provider = MockProvider()
        assert provider.get_logical_id(MyResource) == "MyResource"

    def test_get_logical_id_custom(self):
        """Test get_logical_id respects _logical_id attribute."""

        @wetwire
        class MyResource:
            _logical_id = "CustomLogicalId"
            name: str = "test"

        provider = MockProvider()
        assert provider.get_logical_id(MyResource) == "CustomLogicalId"

    def test_repr(self):
        """Test provider string representation."""
        provider = MockProvider()
        assert "MockProvider" in repr(provider)
        assert "mock" in repr(provider)


class TestProviderTemplateIntegration:
    """Tests for Provider with Template."""

    def test_serialize_template_empty(self):
        """Test serializing empty template."""
        provider = MockProvider()
        template = Template()
        result = provider.serialize_template(template)
        assert result == {}

    def test_serialize_template_with_description(self):
        """Test serializing template with description."""
        provider = MockProvider()
        template = Template(description="My Stack")
        result = provider.serialize_template(template)
        assert result["Description"] == "My Stack"

    def test_serialize_template_with_resources(self):
        """Test serializing template with resources."""

        @wetwire
        class ResourceA:
            name: str = "a"

        @wetwire
        class ResourceB:
            name: str = "b"

        provider = MockProvider()
        template = Template.from_registry()
        result = provider.serialize_template(template)

        assert "Resources" in result
        assert "ResourceA" in result["Resources"]
        assert "ResourceB" in result["Resources"]

    def test_serialize_template_with_parameters(self):
        """Test serializing template with parameters."""
        provider = MockProvider()
        template = Template(parameters={"Env": {"Type": "String"}})
        result = provider.serialize_template(template)
        assert result["Parameters"] == {"Env": {"Type": "String"}}

    def test_serialize_template_with_outputs(self):
        """Test serializing template with outputs."""
        provider = MockProvider()
        template = Template(outputs={"BucketArn": {"Value": "arn:..."}})
        result = provider.serialize_template(template)
        assert result["Outputs"] == {"BucketArn": {"Value": "arn:..."}}

    def test_serialize_template_with_conditions(self):
        """Test serializing template with conditions."""
        provider = MockProvider()
        template = Template(conditions={"IsProd": True})
        result = provider.serialize_template(template)
        assert result["Conditions"] == {"IsProd": True}

    def test_serialize_template_with_mappings(self):
        """Test serializing template with mappings."""
        provider = MockProvider()
        template = Template(mappings={"RegionMap": {"us-east-1": {"ami": "ami-123"}}})
        result = provider.serialize_template(template)
        assert "Mappings" in result

    def test_serialize_template_with_metadata(self):
        """Test serializing template with metadata."""
        provider = MockProvider()
        template = Template(metadata={"Version": "1.0"})
        result = provider.serialize_template(template)
        assert result["Metadata"] == {"Version": "1.0"}

    def test_template_to_dict_with_provider(self):
        """Test Template.to_dict uses provider."""

        @wetwire
        class MyResource:
            name: str = "test"

        provider = MockProvider()
        template = Template.from_registry()
        result = template.to_dict(provider=provider)

        # Should use provider's format
        assert "Resources" in result
        assert result["Resources"]["MyResource"]["Type"] == "Mock::Resource"

    def test_template_to_json_with_provider(self):
        """Test Template.to_json uses provider."""
        import json

        @wetwire
        class MyResource:
            name: str = "test"

        provider = MockProvider()
        template = Template.from_registry()
        result = template.to_json(provider=provider)

        parsed = json.loads(result)
        assert "Resources" in parsed
