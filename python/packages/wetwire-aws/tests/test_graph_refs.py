"""Tests for graph-refs integration.

Note: Classes must be defined at module level for graph-refs introspection
to work correctly with PEP 563 (from __future__ import annotations).
"""

from __future__ import annotations

import pytest
from graph_refs import Attr, ContextRef, Ref, RefList, get_dependencies, get_refs
from wetwire import topological_sort

from wetwire_aws import CloudFormationTemplate, get_att, wetwire_aws
from wetwire_aws.decorator import get_aws_registry
from wetwire_aws.intrinsics.refs import ARN, resolve_refs_from_annotations
from wetwire_aws.resources.iam import Role
from wetwire_aws.resources.lambda_ import Function
from wetwire_aws.resources.s3 import Bucket


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear the registry before and after each test."""
    get_aws_registry().clear()
    yield
    get_aws_registry().clear()


# ============================================================================
# Module-level wrapper classes for graph-refs introspection tests
# ============================================================================


@wetwire_aws
class TestBucket:
    resource: Bucket
    bucket_name = "test-bucket"


@wetwire_aws
class TestRole:
    resource: Role
    role_name = "test-role"


@wetwire_aws
class TestFunctionWithRef:
    resource: Function
    function_name = "test-with-ref"
    # Using Ref[T] annotation for introspection
    # Note: bucket isn't a real Function field, this tests the mechanism
    bucket: Ref[TestBucket] = None


@wetwire_aws
class TestFunctionWithAttr:
    resource: Function
    function_name = "test-with-attr"
    # role IS a real Function field
    role: Attr[TestRole, ARN] = None


@wetwire_aws
class TestFunctionWithBoth:
    resource: Function
    function_name = "test-with-both"
    role: Attr[TestRole, ARN] = None


# For dependency chain test
@wetwire_aws
class NetworkBucket:
    resource: Bucket
    bucket_name = "network"


@wetwire_aws
class SubnetBucket:
    resource: Bucket
    bucket_name = "subnet"
    network: Ref[NetworkBucket] = None


@wetwire_aws
class InstanceBucket:
    resource: Bucket
    bucket_name = "instance"
    subnet: Ref[SubnetBucket] = None


# For direct ref() pattern test
@wetwire_aws
class DirectPatternRole:
    resource: Role
    role_name = "direct-pattern"


@wetwire_aws
class DirectPatternFunction:
    resource: Function
    function_name = "direct"
    role = get_att(DirectPatternRole, "Arn")


@wetwire_aws
class AnnotationPatternRole:
    resource: Role
    role_name = "annotation-pattern"


@wetwire_aws
class AnnotationPatternFunction:
    resource: Function
    function_name = "annotated"
    role: Attr[AnnotationPatternRole, ARN] = None


# ============================================================================
# Test classes
# ============================================================================


class TestGraphRefsIntrospection:
    """Test that graph-refs can introspect wrapper classes."""

    def test_ref_detected(self):
        """Test that Ref[T] annotations are detected by graph-refs."""
        refs = get_refs(TestFunctionWithRef)
        assert "bucket" in refs
        assert refs["bucket"].target == TestBucket

    def test_attr_detected(self):
        """Test that Attr[T, 'name'] annotations are detected by graph-refs."""
        refs = get_refs(TestFunctionWithAttr)
        assert "role" in refs
        assert refs["role"].target == TestRole
        assert refs["role"].attr == "Arn"

    def test_dependencies_computed(self):
        """Test that get_dependencies() works with wrapper classes."""
        deps = get_dependencies(TestFunctionWithBoth)
        assert TestRole in deps

    def test_transitive_dependencies(self):
        """Test that transitive dependencies are computed."""
        # Direct dependencies
        direct_deps = get_dependencies(InstanceBucket, transitive=False)
        assert SubnetBucket in direct_deps
        assert NetworkBucket not in direct_deps

        # Transitive dependencies
        all_deps = get_dependencies(InstanceBucket, transitive=True)
        assert SubnetBucket in all_deps
        assert NetworkBucket in all_deps


class TestGraphRefsSerialization:
    """Test that graph-refs annotations are serialized to CloudFormation."""

    def test_attr_serializes_to_cf_getatt(self):
        """Test that Attr[T, 'name'] serializes to {"Fn::GetAtt": ["T", "name"]}."""
        # Re-register the classes since autouse fixture cleared them
        registry = get_aws_registry()
        registry.register(TestRole, "AWS::IAM::Role")
        registry.register(TestFunctionWithAttr, "AWS::Lambda::Function")

        template = CloudFormationTemplate.from_registry()
        output = template.to_dict()

        # Check that TestFunctionWithAttr.Role has GetAtt
        func_props = output["Resources"]["TestFunctionWithAttr"]["Properties"]
        assert func_props["Role"] == {"Fn::GetAtt": ["TestRole", "Arn"]}

    def test_resolve_refs_from_annotations(self):
        """Test the resolve_refs_from_annotations helper."""
        instance = TestFunctionWithAttr()
        resolved = resolve_refs_from_annotations(instance)

        assert "role" in resolved
        assert resolved["role"].to_dict() == {"Fn::GetAtt": ["TestRole", "Arn"]}


class TestMixedPatterns:
    """Test mixing graph-refs annotations with direct ref() calls."""

    def test_direct_ref_still_works(self):
        """Test that ref(Class) pattern still works."""
        registry = get_aws_registry()
        registry.register(DirectPatternRole, "AWS::IAM::Role")
        registry.register(DirectPatternFunction, "AWS::Lambda::Function")

        template = CloudFormationTemplate.from_registry()
        output = template.to_dict()

        func_props = output["Resources"]["DirectPatternFunction"]["Properties"]
        assert func_props["Role"] == {"Fn::GetAtt": ["DirectPatternRole", "Arn"]}

    def test_annotation_pattern_enables_introspection(self):
        """Test that annotation pattern enables introspection unlike direct pattern."""
        # Direct pattern - no dependencies detected
        direct_deps = get_dependencies(DirectPatternFunction)
        assert len(direct_deps) == 0

        # Annotation pattern - with introspection
        annotated_deps = get_dependencies(AnnotationPatternFunction)
        assert AnnotationPatternRole in annotated_deps


# ============================================================================
# ContextRef test classes (for pseudo-parameters)
# ============================================================================


@wetwire_aws
class ResourceWithContext:
    resource: Bucket
    bucket_name = "context-test"
    # Use ContextRef for pseudo-parameters
    region: ContextRef["AWS::Region"] = None  # noqa: F722


# ============================================================================
# RefList test classes (for list references)
# ============================================================================


@wetwire_aws
class SecurityGroupBucket:
    resource: Bucket
    bucket_name = "sg-bucket"


@wetwire_aws
class InstanceWithSecurityGroups:
    resource: Bucket  # Using Bucket as placeholder
    bucket_name = "instance-bucket"
    security_groups: RefList[SecurityGroupBucket] = None


class TestContextRef:
    """Test ContextRef for pseudo-parameters."""

    def test_context_ref_detected(self):
        """Test that ContextRef annotations are detected by graph-refs."""
        refs = get_refs(ResourceWithContext)
        assert "region" in refs
        assert refs["region"].is_context is True
        assert refs["region"].attr == "AWS::Region"

    def test_context_ref_resolves_to_ref_intrinsic(self):
        """Test that ContextRef resolves to CloudFormation Ref."""
        instance = ResourceWithContext()
        resolved = resolve_refs_from_annotations(instance)

        assert "region" in resolved
        assert resolved["region"].to_dict() == {"Ref": "AWS::Region"}


class TestRefList:
    """Test RefList for list references."""

    def test_reflist_detected(self):
        """Test that RefList annotations are detected by graph-refs."""
        refs = get_refs(InstanceWithSecurityGroups)
        assert "security_groups" in refs
        assert refs["security_groups"].is_list is True
        assert refs["security_groups"].target == SecurityGroupBucket

    def test_reflist_dependencies(self):
        """Test that RefList creates dependencies."""
        deps = get_dependencies(InstanceWithSecurityGroups)
        assert SecurityGroupBucket in deps


class TestTopologicalSort:
    """Test that resources are topologically sorted in templates."""

    def test_topological_sort_orders_by_dependencies(self):
        """Test that topological_sort orders classes by dependencies."""
        # Test the core topological_sort function
        classes = [InstanceBucket, NetworkBucket, SubnetBucket]

        sorted_classes = topological_sort(classes)

        # Get the order of class names
        class_order = [c.__name__ for c in sorted_classes]

        # NetworkBucket before SubnetBucket (dependency)
        assert class_order.index("NetworkBucket") < class_order.index("SubnetBucket")
        # SubnetBucket before InstanceBucket (dependency)
        assert class_order.index("SubnetBucket") < class_order.index("InstanceBucket")

    def test_topological_sort_handles_no_dependencies(self):
        """Test topological sort with classes that have no dependencies."""
        classes = [TestBucket, TestRole]

        sorted_classes = topological_sort(classes)

        # Both should be included
        assert len(sorted_classes) == 2
        class_names = [c.__name__ for c in sorted_classes]
        assert "TestBucket" in class_names
        assert "TestRole" in class_names
