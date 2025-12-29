"""
CLI utilities for wetwire-aws.

Re-exports CLI utilities from dataclass-dsl for backward compatibility.
Domain-specific CLI commands are in cli.py.
"""

from __future__ import annotations

# Re-export from dataclass-dsl for backward compatibility
from dataclass_dsl import (
    add_common_args,
    create_list_command,
    create_validate_command,
    discover_resources,
)

__all__ = [
    "discover_resources",
    "add_common_args",
    "create_list_command",
    "create_validate_command",
]
