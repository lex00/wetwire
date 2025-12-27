"""
Resource loader with topological import ordering.

This module provides setup_resources() which:
1. Discovers Python files in a package directory
2. Parses them to find class definitions and reference annotations
3. Builds a dependency graph from Ref[T], Attr[T, ...] patterns
4. Imports modules in topological order
5. Injects already-loaded classes into each module's namespace
6. Generates .pyi stubs for IDE support

Usage in a resources package __init__.py:
    from wetwire.loader import setup_resources
    setup_resources(__file__, __name__, globals())

Or with domain-specific configuration:
    from wetwire_aws.loader import setup_resources
    setup_resources(__file__, __name__, globals())
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from wetwire.stubs import StubConfig, find_class_definitions, generate_stub_file


def find_wetwire_refs_in_source(source: str) -> set[str]:
    """Extract class names from wetwire reference patterns.

    Matches patterns used by wetwire/graph-refs:

    Type annotation patterns:
    - Ref[ClassName]
    - Attr[ClassName, ...]
    - RefList[ClassName]
    - RefDict[..., ClassName]

    No-parens patterns (value assignments):
    - ClassName.Attribute (e.g., MyRole.Arn)
    - = ClassName  (direct class reference, e.g., vpc = MyVPC)

    Args:
        source: Python source code text

    Returns:
        Set of class names referenced in patterns
    """
    refs: set[str] = set()

    # Match Ref[ClassName]
    for match in re.finditer(r"\bRef\[([A-Za-z_]\w*)\]", source):
        refs.add(match.group(1))

    # Match Attr[ClassName, ...] - class name is first type argument
    for match in re.finditer(r"\bAttr\[([A-Za-z_]\w*)\s*,", source):
        refs.add(match.group(1))

    # Match RefList[ClassName]
    for match in re.finditer(r"\bRefList\[([A-Za-z_]\w*)\]", source):
        refs.add(match.group(1))

    # Match RefDict[..., ClassName] - class name is second type argument
    for match in re.finditer(r"\bRefDict\[[^,]+,\s*([A-Za-z_]\w*)\]", source):
        refs.add(match.group(1))

    # Match no-parens attribute pattern: ClassName.Attribute
    # e.g., role = MyRole.Arn
    # Must be PascalCase to avoid matching module.function patterns
    for match in re.finditer(r"\b([A-Z][A-Za-z0-9]*)\.[A-Z][A-Za-z0-9]*\b", source):
        refs.add(match.group(1))

    # Match no-parens class reference: = ClassName (at end of line or before comment)
    # e.g., vpc = MyVPC
    # Must be PascalCase to avoid matching = some_variable
    for match in re.finditer(r"=\s+([A-Z][A-Za-z0-9]*)\s*(?:#|$)", source, re.MULTILINE):
        refs.add(match.group(1))

    return refs


def _topological_sort(deps: dict[str, set[str]]) -> list[str]:
    """Kahn's algorithm for topological sort with cycle handling.

    Args:
        deps: Dict mapping module name to set of module names it depends on.

    Returns:
        List of module names in dependency order (dependencies first).
        Handles cycles by breaking them and continuing the sort.
    """
    # Make a mutable copy of deps
    remaining_deps: dict[str, set[str]] = {m: set(d) for m, d in deps.items()}

    result: list[str] = []

    while remaining_deps:
        # Find modules with no remaining dependencies
        ready = [m for m, d in remaining_deps.items() if len(d) == 0]

        if ready:
            # Process modules with no dependencies
            for m in sorted(ready):  # Sort for determinism
                result.append(m)
                del remaining_deps[m]
                # Remove this module from others' dependency sets
                for other_deps in remaining_deps.values():
                    other_deps.discard(m)
        else:
            # All remaining modules have dependencies -> there's a cycle
            # Find the module that is depended upon by most other remaining
            # modules - this breaks the cycle at a "hub" node
            dep_count: dict[str, int] = {m: 0 for m in remaining_deps}
            for d in remaining_deps.values():
                for dep in d:
                    if dep in dep_count:
                        dep_count[dep] += 1

            # Pick the most-depended-upon module, with alphabetical tiebreaker
            cycle_breaker = max(
                remaining_deps.keys(),
                key=lambda m: (dep_count[m], -ord(m[0]) if m else 0, m),
            )
            result.append(cycle_breaker)
            del remaining_deps[cycle_breaker]
            # Remove this module from others' dependency sets
            for other_deps in remaining_deps.values():
                other_deps.discard(cycle_breaker)

    return result


def setup_resources(
    init_file: str,
    package_name: str,
    package_globals: dict[str, Any],
    *,
    stub_config: StubConfig | None = None,
    generate_stubs: bool = True,
) -> None:
    """Set up resource imports with topological ordering.

    This function:
    1. Finds all .py files in the package directory
    2. Parses them to find class definitions and Ref/Attr annotations
    3. Builds a dependency graph from the annotations
    4. Imports modules in topological order
    5. Injects previously-loaded classes into each module's namespace
    6. Optionally generates .pyi stubs for IDE support

    Args:
        init_file: Path to __init__.py (__file__)
        package_name: Package name (__name__)
        package_globals: Package globals dict (globals())
        stub_config: Optional stub generation configuration
        generate_stubs: Whether to generate .pyi files (default: True)

    Example:
        # In myapp/resources/__init__.py
        from wetwire.loader import setup_resources
        setup_resources(__file__, __name__, globals())
    """
    pkg_path = Path(init_file).parent

    # 1. Discover module files and their class definitions/references
    module_sources: dict[str, str] = {}
    module_classes: dict[str, list[str]] = {}

    for file in pkg_path.glob("*.py"):
        if file.name.startswith("_"):
            continue
        source = file.read_text()
        module_name = file.stem
        module_sources[module_name] = source
        module_classes[module_name] = find_class_definitions(source)

    # 2. Build class -> module map
    class_to_module: dict[str, str] = {}
    for mod, classes in module_classes.items():
        for cls in classes:
            class_to_module[cls] = mod

    # 3. Build dependency graph (module -> set of modules it depends on)
    deps: dict[str, set[str]] = {mod: set() for mod in module_sources}
    for mod, source in module_sources.items():
        for ref_class in find_wetwire_refs_in_source(source):
            if ref_class in class_to_module:
                dep_mod = class_to_module[ref_class]
                if dep_mod != mod:
                    deps[mod].add(dep_mod)

    # 4. Topological sort
    import_order = _topological_sort(deps)

    # 5. Import in order, injecting shared namespace BEFORE each module executes
    shared_namespace: dict[str, Any] = {}
    all_names: list[str] = []

    for mod_name in import_order:
        full_mod_name = f"{package_name}.{mod_name}"

        # Skip if already imported (shouldn't happen with topological order)
        if full_mod_name in sys.modules:
            module = sys.modules[full_mod_name]
        else:
            # Load module with namespace injection BEFORE execution
            module = _load_module_with_namespace(
                mod_name, full_mod_name, pkg_path, shared_namespace
            )

        # Extract classes from this module and add to shared namespace
        for cls_name in module_classes.get(mod_name, []):
            if hasattr(module, cls_name):
                obj = getattr(module, cls_name)
                shared_namespace[cls_name] = obj
                package_globals[cls_name] = obj
                all_names.append(cls_name)

    # 6. Set __all__ for star imports
    package_globals["__all__"] = all_names

    # 7. Generate stubs for IDE support
    if generate_stubs:
        generate_stub_file(pkg_path, all_names, module_classes, config=stub_config)


def _load_module_with_namespace(
    mod_name: str,
    full_mod_name: str,
    pkg_path: Path,
    namespace: dict[str, Any],
) -> ModuleType:
    """Load a module, injecting namespace before execution.

    This allows Ref[ClassName] and Attr[ClassName, ...] to resolve
    during class body evaluation when ClassName is defined in another file.

    Args:
        mod_name: Short module name (e.g., "compute")
        full_mod_name: Full module name (e.g., "myapp.resources.compute")
        pkg_path: Path to the package directory
        namespace: Shared namespace with already-loaded classes

    Returns:
        The loaded module
    """
    file_path = pkg_path / f"{mod_name}.py"

    # Create module spec
    spec = importlib.util.spec_from_file_location(full_mod_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {full_mod_name} from {file_path}")

    # Create module object
    module = importlib.util.module_from_spec(spec)

    # Inject shared namespace BEFORE execution
    # This makes sibling resource classes available during class body evaluation
    for name, obj in namespace.items():
        setattr(module, name, obj)

    # Register in sys.modules before execution (standard Python behavior)
    sys.modules[full_mod_name] = module

    # Execute the module code
    spec.loader.exec_module(module)

    return module
