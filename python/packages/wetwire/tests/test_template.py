"""Tests for Template class."""

import json

from wetwire import Template, wetwire


class TestTemplate:
    """Tests for Template class."""

    def test_empty_template(self):
        """Test creating an empty template."""
        template = Template()
        assert template.description == ""
        assert template.resources == []
        assert len(template) == 0

    def test_template_with_description(self):
        """Test template with description."""
        template = Template(description="My Stack")
        assert template.description == "My Stack"

    def test_from_registry_empty(self):
        """Test from_registry with no resources."""
        template = Template.from_registry()
        assert len(template) == 0

    def test_from_registry_with_resources(self):
        """Test from_registry collects registered resources."""

        @wetwire
        class ResourceA:
            name: str = "a"

        @wetwire
        class ResourceB:
            name: str = "b"

        template = Template.from_registry()
        assert len(template) == 2

    def test_from_registry_with_scope(self):
        """Test from_registry filters by scope."""

        @wetwire
        class ResourceA:
            name: str = "a"

        # Manually set module to simulate different packages
        ResourceA.__module__ = "myapp.prod.resources"

        @wetwire
        class ResourceB:
            name: str = "b"

        ResourceB.__module__ = "myapp.dev.resources"

        template = Template.from_registry(scope_package="myapp.prod")
        assert len(template) == 1

    def test_add_resource(self):
        """Test adding resources manually."""
        template = Template()

        @wetwire
        class MyResource:
            name: str = "test"

        instance = MyResource()
        template.add_resource(instance)
        assert len(template) == 1

    def test_to_dict_empty(self):
        """Test to_dict with empty template."""
        template = Template()
        result = template.to_dict()
        assert result == {}

    def test_to_dict_with_description(self):
        """Test to_dict includes description."""
        template = Template(description="Test Stack")
        result = template.to_dict()
        assert result["description"] == "Test Stack"

    def test_to_dict_with_resources(self):
        """Test to_dict includes resources."""

        @wetwire
        class MyResource:
            name: str = "test"

        template = Template.from_registry()
        result = template.to_dict()
        assert "resources" in result
        assert len(result["resources"]) == 1
        assert result["resources"][0]["class"] == "MyResource"

    def test_to_dict_with_parameters(self):
        """Test to_dict includes parameters."""
        template = Template(parameters={"Environment": {"Type": "String"}})
        result = template.to_dict()
        assert result["parameters"] == {"Environment": {"Type": "String"}}

    def test_to_dict_with_outputs(self):
        """Test to_dict includes outputs."""
        template = Template(outputs={"BucketArn": {"Value": "arn:..."}})
        result = template.to_dict()
        assert result["outputs"] == {"BucketArn": {"Value": "arn:..."}}

    def test_to_dict_with_conditions(self):
        """Test to_dict includes conditions."""
        template = Template(conditions={"IsProd": {"Fn::Equals": ["prod", "prod"]}})
        result = template.to_dict()
        assert "conditions" in result

    def test_to_dict_with_mappings(self):
        """Test to_dict includes mappings."""
        template = Template(mappings={"RegionMap": {"us-east-1": {"AMI": "ami-123"}}})
        result = template.to_dict()
        assert "mappings" in result

    def test_to_dict_with_metadata(self):
        """Test to_dict includes metadata."""
        template = Template(metadata={"Version": "1.0"})
        result = template.to_dict()
        assert result["metadata"] == {"Version": "1.0"}

    def test_to_json(self):
        """Test JSON serialization."""
        template = Template(description="Test")
        result = template.to_json()
        parsed = json.loads(result)
        assert parsed["description"] == "Test"

    def test_to_json_with_indent(self):
        """Test JSON serialization with custom indent."""
        template = Template(description="Test")
        result = template.to_json(indent=4)
        assert "    " in result  # 4-space indent

    def test_to_yaml(self):
        """Test YAML serialization."""
        template = Template(description="Test")
        result = template.to_yaml()
        assert "description: Test" in result

    def test_validate_no_errors(self):
        """Test validation passes with no issues."""

        @wetwire
        class ResourceA:
            name: str = "a"

        @wetwire
        class ResourceB:
            name: str = "b"

        template = Template.from_registry()
        errors = template.validate()
        assert errors == []

    def test_validate_duplicate_names(self):
        """Test validation catches duplicate resource names."""

        @wetwire
        class MyResource:
            name: str = "test"

        template = Template()
        instance1 = MyResource()
        instance2 = MyResource()
        template.add_resource(instance1)
        template.add_resource(instance2)

        errors = template.validate()
        assert len(errors) == 1
        assert "Duplicate" in errors[0]

    def test_repr(self):
        """Test string representation."""
        template = Template(description="My Stack")
        assert "My Stack" in repr(template)
        assert "resources=0" in repr(template)

    def test_get_dependency_order_empty(self):
        """Test dependency ordering with no resources."""
        template = Template()
        result = template.get_dependency_order()
        assert result == []

    def test_get_dependency_order(self):
        """Test dependency ordering returns resources."""
        from graph_refs import Ref

        @wetwire
        class ResourceA:
            name: str = "a"

        @wetwire
        class ResourceB:
            dep: Ref[ResourceA] = None
            name: str = "b"

        template = Template.from_registry()
        ordered = template.get_dependency_order()
        assert len(ordered) == 2
        # ResourceA should come before ResourceB
        class_order = [type(r).__name__ for r in ordered]
        assert class_order.index("ResourceA") < class_order.index("ResourceB")
