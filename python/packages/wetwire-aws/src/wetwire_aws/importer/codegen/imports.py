"""Import statement generation.

This module generates the import section for generated Python files,
organizing imports by category.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .context import CodegenContext


def generate_imports(ctx: CodegenContext) -> str:
    """Generate import statements for a code file.

    Formats all imports collected in the context into properly
    grouped and sorted import statements.

    Args:
        ctx: Code generation context with accumulated imports.

    Returns:
        Formatted import statements as a string.
    """
    lines = []

    # Core wetwire_aws imports
    core_imports = ctx.imports.get("wetwire_aws", set())
    if core_imports:
        sorted_imports = sorted(core_imports)
        if len(sorted_imports) <= 3:
            lines.append(f"from wetwire_aws import {', '.join(sorted_imports)}")
        else:
            lines.append("from wetwire_aws import (")
            for name in sorted_imports:
                lines.append(f"    {name},")
            lines.append(")")

    # Base class imports
    base_imports = ctx.imports.get("wetwire_aws.base", set())
    if base_imports:
        sorted_imports = sorted(base_imports)
        lines.append(f"from wetwire_aws.base import {', '.join(sorted_imports)}")

    # Resource module imports (e.g., from wetwire_aws.resources import s3)
    resource_module_imports = ctx.imports.get("wetwire_aws.resources", set())
    if resource_module_imports:
        sorted_imports = sorted(resource_module_imports)
        if len(sorted_imports) <= 3:
            lines.append(
                f"from wetwire_aws.resources import {', '.join(sorted_imports)}"
            )
        else:
            lines.append("from wetwire_aws.resources import (")
            for name in sorted_imports:
                lines.append(f"    {name},")
            lines.append(")")

    # Resource class imports (e.g., from wetwire_aws.resources.s3 import Bucket)
    resource_modules = sorted(
        (mod, names)
        for mod, names in ctx.imports.items()
        if mod.startswith("wetwire_aws.resources.") and mod != "wetwire_aws.resources"
    )
    for module, names in resource_modules:
        sorted_names = sorted(names)
        if len(sorted_names) <= 3:
            lines.append(f"from {module} import {', '.join(sorted_names)}")
        else:
            lines.append(f"from {module} import (")
            for name in sorted_names:
                lines.append(f"    {name},")
            lines.append(")")

    # Intrinsic imports
    if ctx.intrinsic_imports:
        sorted_intrinsics = sorted(ctx.intrinsic_imports)
        if len(sorted_intrinsics) <= 3:
            lines.append(
                f"from wetwire_aws.intrinsics import {', '.join(sorted_intrinsics)}"
            )
        else:
            lines.append("from wetwire_aws.intrinsics import (")
            for name in sorted_intrinsics:
                lines.append(f"    {name},")
            lines.append(")")

    # Constants imports (condition operators like BOOL, STRING_EQUALS, etc.)
    constants_imports = ctx.imports.get("wetwire_aws.constants", set())
    if constants_imports:
        sorted_constants = sorted(constants_imports)
        if len(sorted_constants) <= 3:
            lines.append(
                f"from wetwire_aws.constants import {', '.join(sorted_constants)}"
            )
        else:
            lines.append("from wetwire_aws.constants import (")
            for name in sorted_constants:
                lines.append(f"    {name},")
            lines.append(")")

    return "\n".join(lines)
