"""
Stub file generator for IDE type checking.

Generates .pyi files so IDEs can understand dynamic imports from
setup_resources(). Works with Pylance, mypy, and other type checkers.

The `from . import *` pattern requires stub files for IDE autocomplete
because static analyzers can't see dynamic exports from setup_resources().

Usage:
    from wetwire.stubs import generate_stub_file, StubConfig

    config = StubConfig(
        package_name="wetwire_aws",
        core_imports=["wetwire_aws", "CloudFormationResource", ...],
        expand_star_imports={"wetwire_aws": [...names...]},
    )
    generate_stub_file(package_path, all_names, module_classes, config=config)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StubConfig:
    """Configuration for domain-specific stub generation.

    Domain packages provide this to customize how stubs are generated
    for their specific package structure and imports.

    Attributes:
        package_name: The domain package name (e.g., "wetwire_aws")
        core_imports: Names that should be available from the domain package
        expand_star_imports: Map of module -> names for expanding star imports
        extra_header_lines: Additional lines to add to stub header
    """

    package_name: str = ""
    core_imports: list[str] = field(default_factory=list)
    expand_star_imports: dict[str, list[str]] = field(default_factory=dict)
    extra_header_lines: list[str] = field(default_factory=list)


# Default wetwire core exports (for base wetwire usage)
WETWIRE_CORE_EXPORTS = [
    "__version__",
    "wetwire",
    "registry",
    "ResourceRegistry",
    "Template",
    "Provider",
    "Context",
    "PROJECT",
    "ENVIRONMENT",
    "computed",
    "when",
    "match",
    "topological_sort",
    "get_creation_order",
    "get_deletion_order",
    "detect_cycles",
    "get_dependency_graph",
    "discover_resources",
    "add_common_args",
    "create_list_command",
    "create_validate_command",
    "Ref",
    "Attr",
    "RefList",
    "RefDict",
    "ContextRef",
    "RefInfo",
    "get_refs",
    "get_ref_dependencies",
    "setup_resources",
    "StubConfig",
]


def find_class_definitions(source: str) -> list[str]:
    """Extract class names defined in a source file.

    Args:
        source: Python source code text

    Returns:
        List of class names found in the source
    """
    return re.findall(r"^class\s+(\w+)", source, re.MULTILINE)


def expand_star_import(
    import_line: str,
    config: StubConfig | None = None,
) -> tuple[str, list[str]]:
    """Expand a star import to explicit imports if from a known module.

    For known modules (like wetwire), expands `from x import *` to
    explicit imports so Pylance can resolve them.

    Args:
        import_line: An import statement line
        config: Optional domain-specific stub configuration

    Returns:
        Tuple of (expanded_import_line, list_of_names).
        If not a star import or unknown module, returns original line
        with empty list.
    """
    clean_line = import_line
    if "#" in clean_line:
        clean_line = clean_line.split("#")[0].strip()

    # Check wetwire core
    if "from wetwire import *" in clean_line:
        names = sorted(WETWIRE_CORE_EXPORTS)
        expanded = f"from wetwire import {', '.join(names)}"
        return expanded, names

    # Check domain-specific expansions
    if config:
        for pattern, names in config.expand_star_imports.items():
            if f"from {pattern} import *" in clean_line:
                sorted_names = sorted(names)
                expanded = f"from {pattern} import {', '.join(sorted_names)}"
                return expanded, sorted_names

    return import_line, []


def extract_import_names(import_stmt: str) -> list[str]:
    """Extract imported names from an import statement.

    Handles:
    - from x import a, b, c
    - from x import (a, b, c)
    - from x import a as alias
    - from x import *  (returns empty list - star imports handled separately)
    - import x, y, z
    - Comments like # noqa: F403 are stripped

    Args:
        import_stmt: An import statement string

    Returns:
        List of imported names
    """
    names: list[str] = []

    # Remove newlines and extra whitespace
    import_stmt = " ".join(import_stmt.split())

    # Strip trailing comments (e.g., # noqa: F403)
    if "#" in import_stmt:
        import_stmt = import_stmt.split("#")[0].strip()

    if import_stmt.startswith("from "):
        # from x import a, b, c  OR  from x import (a, b, c)
        if " import " in import_stmt:
            imports_part = import_stmt.split(" import ", 1)[1]
            # Remove parentheses
            imports_part = imports_part.replace("(", "").replace(")", "")

            # Handle star imports - return empty (caller handles these specially)
            if imports_part.strip() == "*":
                return []

            # Split by comma
            for item in imports_part.split(","):
                item = item.strip()
                if " as " in item:
                    # from x import a as b -> use 'b'
                    names.append(item.split(" as ")[1].strip())
                elif item and item != "*":
                    names.append(item)
    elif import_stmt.startswith("import "):
        # import x, y, z
        imports_part = import_stmt[7:]  # Remove "import "
        for item in imports_part.split(","):
            item = item.strip()
            if " as " in item:
                names.append(item.split(" as ")[1].strip())
            elif item:
                # For 'import x.y.z', the available name is 'x'
                names.append(item.split(".")[0])

    return names


def generate_stub_file(
    package_path: Path,
    all_names: list[str] | None = None,
    module_classes: dict[str, list[str]] | None = None,
    *,
    config: StubConfig | None = None,
) -> bool:
    """Generate .pyi stub file for IDE type checking.

    This allows IDEs like VSCode/Pylance to understand what names are
    exported from resource packages, even though they're loaded dynamically.

    Args:
        package_path: Path to the package directory
        all_names: Optional list of all exported names
        module_classes: Optional dict of module -> class names
        config: Optional domain-specific configuration

    Returns:
        True if stubs were generated/updated, False if unchanged
    """
    if module_classes is None:
        module_classes = {}
        for file in package_path.glob("*.py"):
            if file.name.startswith("_"):
                continue
            source = file.read_text()
            module_name = file.stem
            module_classes[module_name] = find_class_definitions(source)

    if all_names is None:
        all_names = []
        for classes in module_classes.values():
            all_names.extend(classes)

    # Build stub content
    init_stub_path = package_path / "__init__.pyi"
    init_lines = ['"""Auto-generated stub for IDE type checking."""', ""]

    # Add extra header lines from config
    if config and config.extra_header_lines:
        init_lines.extend(config.extra_header_lines)
        init_lines.append("")

    # Read __init__.py to extract and process imports
    init_file = package_path / "__init__.py"
    imported_names: list[str] = []

    if init_file.exists():
        init_source = init_file.read_text()
        in_import = False
        import_buffer: list[str] = []

        for line in init_source.splitlines():
            # Skip setup_resources call and comments
            if "setup_resources(" in line or line.strip().startswith("#"):
                continue

            if in_import:
                import_buffer.append(line)
                if ")" in line:
                    # End of multi-line import
                    full_import = "\n".join(import_buffer)
                    init_lines.append(full_import)
                    imported_names.extend(extract_import_names(full_import))
                    import_buffer = []
                    in_import = False
            elif line.startswith("from ") or line.startswith("import "):
                if "(" in line and ")" not in line:
                    # Start of multi-line import
                    in_import = True
                    import_buffer = [line]
                else:
                    # Try to expand star imports from known modules
                    expanded_line, star_names = expand_star_import(line, config)
                    init_lines.append(expanded_line)
                    if star_names:
                        imported_names.extend(star_names)
                    else:
                        imported_names.extend(extract_import_names(line))

    init_lines.append("")

    # Re-export all classes from resource modules
    all_resource_classes: list[str] = []
    for mod_name, classes in sorted(module_classes.items()):
        if classes:
            for cls in sorted(classes):
                init_lines.append(f"from .{mod_name} import {cls} as {cls}")
                all_resource_classes.append(cls)

    init_lines.append("")

    # Build __all__ for star imports - Pylance needs this to resolve imports
    all_exports = imported_names + all_resource_classes
    init_lines.append(f"__all__: list[str] = {sorted(set(all_exports))!r}")
    init_lines.append("")

    return _write_stub_if_changed(init_stub_path, "\n".join(init_lines))


def _write_stub_if_changed(stub_path: Path, content: str) -> bool:
    """Write stub file only if content has changed.

    Returns True if file was written, False if unchanged.
    """
    try:
        existing = stub_path.read_text()
        if existing == content:
            return False
    except FileNotFoundError:
        pass

    stub_path.write_text(content)
    return True


def is_resource_package(path: Path) -> bool:
    """Check if a directory is a wetwire resource package.

    A resource package has __init__.py that calls setup_resources().

    Args:
        path: Directory path to check

    Returns:
        True if the directory is a resource package
    """
    init_file = path / "__init__.py"
    if not init_file.exists():
        return False

    content = init_file.read_text()
    return "setup_resources(" in content


def find_resource_packages(root: Path) -> list[Path]:
    """Find all resource packages under a root directory.

    Looks for directories with __init__.py that contain setup_resources().

    Args:
        root: Root directory to search

    Returns:
        List of paths to resource packages
    """
    packages: list[Path] = []

    for init_file in root.rglob("__init__.py"):
        package_dir = init_file.parent
        if is_resource_package(package_dir):
            packages.append(package_dir)

    return packages


def generate_stubs_for_path(
    path: Path,
    config: StubConfig | None = None,
) -> int:
    """Generate stubs for all resource packages under a path.

    Args:
        path: Directory to scan for resource packages
        config: Optional domain-specific configuration

    Returns:
        Number of resource packages processed
    """
    path = path.resolve()

    if is_resource_package(path):
        packages = [path]
    else:
        packages = find_resource_packages(path)

    for package_path in packages:
        generate_stub_file(package_path, config=config)

    return len(packages)
