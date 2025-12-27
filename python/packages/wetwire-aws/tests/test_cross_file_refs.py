"""
Test cross-file references with `from . import *` pattern.

This tests the CRITICAL feature that users can:
1. Define resources in separate files
2. Use `from . import *` in __init__.py
3. Have cross-file references resolve correctly

This is the recommended user pattern and MUST work.
"""

from __future__ import annotations

import pytest
from graph_refs import get_dependencies

from wetwire_aws import CloudFormationTemplate
from wetwire_aws.decorator import get_aws_registry


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear the registry before and after each test."""
    get_aws_registry().clear()
    yield
    get_aws_registry().clear()


class TestCrossFileReferences:
    """Test that resources defined in separate files can reference each other."""

    def test_cross_file_import_star_pattern(self):
        """
        Test that `from . import *` pattern works for cross-file references.

        This simulates a user project structure:
        - resources/__init__.py: `from . import *`
        - resources/role.py: defines AppRole
        - resources/function.py: defines AppFunction with Attr[AppRole, ARN]
        """
        # Import the test package - this uses `from . import *` pattern
        from tests.cross_file_test import AppFunction, AppRole

        # Verify both classes are imported
        assert AppRole is not None
        assert AppFunction is not None

        # Verify the cross-file dependency is detected
        deps = get_dependencies(AppFunction)
        assert AppRole in deps, "AppFunction should depend on AppRole"

    def test_cross_file_serialization(self):
        """Test that cross-file references serialize correctly to CloudFormation."""
        # Import via the package
        from tests.cross_file_test import AppFunction, AppRole

        # Re-register after fixture cleared them
        registry = get_aws_registry()
        registry.register(AppRole, "AWS::IAM::Role")
        registry.register(AppFunction, "AWS::Lambda::Function")

        # Generate template
        template = CloudFormationTemplate.from_registry()
        output = template.to_dict()

        # Verify resources are in the template
        assert "AppRole" in output["Resources"]
        assert "AppFunction" in output["Resources"]

        # Verify the cross-file reference is serialized correctly
        func_props = output["Resources"]["AppFunction"]["Properties"]
        assert func_props["Role"] == {"Fn::GetAtt": ["AppRole", "Arn"]}, \
            "Cross-file Attr[AppRole, ARN] should serialize to GetAtt"

    def test_cross_file_dependency_order(self):
        """Test that cross-file dependencies are ordered correctly."""
        from tests.cross_file_test import AppFunction, AppRole

        # Re-register
        registry = get_aws_registry()
        registry.register(AppRole, "AWS::IAM::Role")
        registry.register(AppFunction, "AWS::Lambda::Function")

        # Generate template
        template = CloudFormationTemplate.from_registry()
        output = template.to_dict()

        # Get resource order
        resource_names = list(output["Resources"].keys())

        # AppRole should come before AppFunction (dependency order)
        role_idx = resource_names.index("AppRole")
        func_idx = resource_names.index("AppFunction")
        assert role_idx < func_idx, \
            "AppRole should appear before AppFunction in template (dependency order)"
