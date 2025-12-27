"""Tests for dependency ordering utilities."""

from dataclasses import dataclass

from graph_refs import Ref

from wetwire import (
    detect_cycles,
    get_creation_order,
    get_deletion_order,
    get_dependency_graph,
    topological_sort,
    wetwire,
)


class Network:
    """Mock network resource."""

    pass


class Subnet:
    """Mock subnet resource."""

    pass


class Instance:
    """Mock instance resource."""

    pass


class TestTopologicalSort:
    """Tests for topological_sort."""

    def test_empty_list(self):
        """Should handle empty list."""
        result = topological_sort([])
        assert result == []

    def test_single_class(self):
        """Should handle single class."""

        @wetwire
        class Single:
            resource: Network

        result = topological_sort([Single])
        assert result == [Single]

    def test_independent_classes(self):
        """Should handle classes with no dependencies."""

        @wetwire
        class A:
            resource: Network

        @wetwire
        class B:
            resource: Network

        result = topological_sort([A, B])
        assert set(result) == {A, B}

    def test_linear_dependencies(self):
        """Should sort linear dependencies correctly."""

        @dataclass
        class MyNetwork:
            name: str = "network"

        @dataclass
        class MySubnet:
            network: Ref[MyNetwork]
            name: str = "subnet"

        @dataclass
        class MyInstance:
            subnet: Ref[MySubnet]
            name: str = "instance"

        result = topological_sort([MyInstance, MySubnet, MyNetwork])

        # Network should come before Subnet, Subnet before Instance
        assert result.index(MyNetwork) < result.index(MySubnet)
        assert result.index(MySubnet) < result.index(MyInstance)


class TestCreationDeletionOrder:
    """Tests for get_creation_order and get_deletion_order."""

    def test_creation_order(self):
        """Dependencies should come before dependents."""

        @dataclass
        class MyNetwork:
            name: str = "network"

        @dataclass
        class MySubnet:
            network: Ref[MyNetwork]
            name: str = "subnet"

        order = get_creation_order([MySubnet, MyNetwork])
        assert order.index(MyNetwork) < order.index(MySubnet)

    def test_deletion_order(self):
        """Dependents should come before dependencies."""

        @dataclass
        class MyNetwork:
            name: str = "network"

        @dataclass
        class MySubnet:
            network: Ref[MyNetwork]
            name: str = "subnet"

        order = get_deletion_order([MySubnet, MyNetwork])
        assert order.index(MySubnet) < order.index(MyNetwork)


class TestDetectCycles:
    """Tests for detect_cycles."""

    def test_no_cycles(self):
        """Should return empty list when no cycles."""

        @dataclass
        class A:
            name: str = "a"

        @dataclass
        class B:
            a: Ref[A]
            name: str = "b"

        cycles = detect_cycles([A, B])
        assert cycles == []

    def test_empty_list(self):
        """Should handle empty list."""
        cycles = detect_cycles([])
        assert cycles == []


class TestDependencyGraph:
    """Tests for get_dependency_graph."""

    def test_builds_graph(self):
        """Should build correct dependency graph."""

        @dataclass
        class MyNetwork:
            name: str = "network"

        @dataclass
        class MySubnet:
            network: Ref[MyNetwork]
            name: str = "subnet"

        graph = get_dependency_graph([MyNetwork, MySubnet])

        assert MyNetwork in graph
        assert MySubnet in graph
        assert graph[MyNetwork] == set()
        assert graph[MySubnet] == {MyNetwork}
