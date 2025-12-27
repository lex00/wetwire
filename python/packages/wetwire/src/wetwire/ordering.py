"""
Dependency ordering utilities for wetwire resources.

Uses graph-refs introspection to compute topological sort and dependency graphs.
"""

from __future__ import annotations

from typing import Any

from graph_refs import get_dependencies


def topological_sort(classes: list[type[Any]]) -> list[type[Any]]:
    """
    Sort classes by dependency order (dependencies first).

    Uses graph_refs.get_dependencies() to compute the dependency graph,
    then performs a topological sort so that dependencies appear before
    dependents.

    Args:
        classes: List of wrapper classes to sort

    Returns:
        Classes sorted in dependency order (dependencies first)

    Raises:
        ValueError: If circular dependencies exist

    Example:
        >>> # Given: Instance depends on Subnet depends on Network
        >>> sorted_classes = topological_sort([Instance, Subnet, Network])
        >>> sorted_classes
        [Network, Subnet, Instance]
    """
    if not classes:
        return []

    class_set = set(classes)
    sorted_result: list[type[Any]] = []
    remaining = set(classes)

    # Track visited to detect cycles
    max_iterations = len(classes) * len(classes)
    iterations = 0

    while remaining:
        iterations += 1
        if iterations > max_iterations:
            # Find classes involved in cycle
            cycle_classes = [c.__name__ for c in remaining]
            raise ValueError(f"Circular dependency detected involving: {cycle_classes}")

        # Find classes whose dependencies are all satisfied
        ready = [
            cls
            for cls in remaining
            if get_dependencies(cls).issubset(
                set(sorted_result) | (set(classes) - class_set)
            )
        ]

        if not ready:
            # All remaining classes have unsatisfied dependencies
            # This indicates a circular dependency
            cycle_classes = [c.__name__ for c in remaining]
            raise ValueError(f"Circular dependency detected involving: {cycle_classes}")

        for cls in ready:
            sorted_result.append(cls)
            remaining.remove(cls)

    return sorted_result


def get_creation_order(classes: list[type[Any]]) -> list[type[Any]]:
    """
    Get the order in which resources should be created.

    Dependencies appear before dependents.

    Args:
        classes: List of wrapper classes

    Returns:
        Classes in creation order (dependencies first)

    Example:
        >>> order = get_creation_order([Instance, Subnet, Network])
        >>> # Network created first, then Subnet, then Instance
    """
    return topological_sort(classes)


def get_deletion_order(classes: list[type[Any]]) -> list[type[Any]]:
    """
    Get the order in which resources should be deleted.

    Dependents appear before dependencies (reverse of creation order).

    Args:
        classes: List of wrapper classes

    Returns:
        Classes in deletion order (dependents first)

    Example:
        >>> order = get_deletion_order([Instance, Subnet, Network])
        >>> # Instance deleted first, then Subnet, then Network
    """
    return list(reversed(topological_sort(classes)))


def detect_cycles(classes: list[type[Any]]) -> list[tuple[type[Any], ...]]:
    """
    Detect circular dependencies in the given classes.

    Uses Tarjan's algorithm to find strongly connected components.

    Args:
        classes: List of wrapper classes to check

    Returns:
        List of tuples, where each tuple contains classes involved in a cycle.
        Empty list if no cycles.

    Example:
        >>> # If A depends on B and B depends on A
        >>> cycles = detect_cycles([A, B])
        >>> cycles
        [(A, B)]
    """
    if not classes:
        return []

    # Build adjacency list
    class_set = set(classes)
    graph: dict[type[Any], set[type[Any]]] = {}
    for cls in classes:
        deps = get_dependencies(cls)
        graph[cls] = deps & class_set  # Only consider deps within our set

    # Tarjan's algorithm for finding SCCs
    index_counter = [0]
    stack: list[type[Any]] = []
    lowlinks: dict[type[Any], int] = {}
    index: dict[type[Any], int] = {}
    on_stack: set[type[Any]] = set()
    sccs: list[tuple[type[Any], ...]] = []

    def strongconnect(v: type[Any]) -> None:
        index[v] = index_counter[0]
        lowlinks[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack.add(v)

        for w in graph.get(v, set()):
            if w not in index:
                strongconnect(w)
                lowlinks[v] = min(lowlinks[v], lowlinks[w])
            elif w in on_stack:
                lowlinks[v] = min(lowlinks[v], index[w])

        if lowlinks[v] == index[v]:
            scc: list[type[Any]] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                scc.append(w)
                if w == v:
                    break
            # Only report as cycle if more than one element
            if len(scc) > 1:
                sccs.append(tuple(scc))

    for cls in classes:
        if cls not in index:
            strongconnect(cls)

    return sccs


def get_dependency_graph(classes: list[type[Any]]) -> dict[type[Any], set[type[Any]]]:
    """
    Build a dependency graph for the given classes.

    Args:
        classes: List of wrapper classes

    Returns:
        Dict mapping each class to its set of dependencies

    Example:
        >>> graph = get_dependency_graph([Instance, Subnet, Network])
        >>> graph[Instance]
        {Subnet}
        >>> graph[Subnet]
        {Network}
        >>> graph[Network]
        set()
    """
    class_set = set(classes)
    return {cls: get_dependencies(cls) & class_set for cls in classes}
