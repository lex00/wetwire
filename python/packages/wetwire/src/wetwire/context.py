"""
Context base class for environment-specific values.

Provides a way to pass environment-specific configuration
to resources at serialization time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from graph_refs import ContextRef


@dataclass
class Context:
    """
    Base context for environment-specific values.

    Subclass to add domain-specific values:

        @dataclass
        class AWSContext(Context):
            account_id: str = ""
            region: str = ""
            stack_name: str = ""

    Example:
        >>> ctx = Context(project="myapp", environment="production")
        >>> ctx.get("project")
        'myapp'
    """

    project: str = ""
    environment: str = ""

    def get(self, name: str, default: Any = None) -> Any:
        """
        Get a context value by name.

        Args:
            name: The context value name
            default: Default value if not found

        Returns:
            The context value or default
        """
        return getattr(self, name, default)

    def resolve(self, context_ref: object) -> Any:
        """
        Resolve a ContextRef to its value.

        Args:
            context_ref: The context reference to resolve

        Returns:
            The resolved value
        """
        # Extract the name from the ContextRef
        # ContextRef["name"] has the name as the type argument
        args = getattr(context_ref, "__args__", ())
        if args:
            name = args[0]
            if isinstance(name, str):
                return self.get(name)
        return None


# Type aliases for common context references
# These are used as type annotations: field: PROJECT
PROJECT = ContextRef[Literal["project"]]
ENVIRONMENT = ContextRef[Literal["environment"]]
