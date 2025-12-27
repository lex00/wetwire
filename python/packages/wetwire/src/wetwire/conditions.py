"""
Conditional value support for environment-specific configuration.

Enables values that vary based on context (environment, region, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from wetwire.context import Context

T = TypeVar("T")


@dataclass
class ConditionalValue:
    """
    Base class for conditional values.

    Conditional values are resolved at serialization time based on context.
    """

    def resolve(self, context: Context) -> Any:
        """
        Resolve the conditional to a concrete value.

        Args:
            context: The context for resolution

        Returns:
            The resolved value
        """
        raise NotImplementedError


@dataclass
class WhenCondition(ConditionalValue):
    """
    A value that depends on a boolean condition.

    Created via the `when()` function.
    """

    condition: Any
    then_value: Any
    else_value: Any

    def resolve(self, context: Context) -> Any:
        """Resolve based on condition."""
        # Evaluate condition
        cond = self.condition
        if callable(cond):
            cond = cond(context)

        if cond:
            return self.then_value
        return self.else_value


@dataclass
class MatchCondition(ConditionalValue):
    """
    A value that depends on pattern matching.

    Created via the `match()` function.
    """

    value: Any
    cases: dict[Any, Any]
    default: Any

    def resolve(self, context: Context) -> Any:
        """Resolve by matching value against cases."""
        # Get the value to match
        val = self.value
        if callable(val):
            val = val(context)
        elif hasattr(val, "get"):
            # It might be a context reference
            try:
                val = context.get(val) if hasattr(context, "get") else val
            except Exception:
                pass

        return self.cases.get(val, self.default)


def when(
    condition: Any,
    then: T,
    else_: T,
) -> T:
    """
    Conditional value based on a boolean condition.

    The condition is evaluated at serialization time with access to context.

    Example:
        >>> @wetwire
        ... class MyDatabase:
        ...     resource: Database
        ...     instance_class = when(
        ...         lambda ctx: ctx.environment == "production",
        ...         then="db.r5.large",
        ...         else_="db.t3.micro",
        ...     )

    Args:
        condition: Boolean value or callable(context) -> bool
        then: Value if condition is True
        else_: Value if condition is False

    Returns:
        A conditional value that resolves at serialization time
    """
    return WhenCondition(condition=condition, then_value=then, else_value=else_)  # type: ignore[return-value]


def match(
    value: Any,
    cases: dict[Any, T],
    default: T | None = None,
) -> T:
    """
    Pattern matching on a value.

    The value is matched against cases at serialization time.

    Example:
        >>> @wetwire
        ... class MyDatabase:
        ...     resource: Database
        ...     instance_class = match(
        ...         lambda ctx: ctx.environment,
        ...         {
        ...             "production": "db.r5.large",
        ...             "staging": "db.t3.medium",
        ...             "development": "db.t3.micro",
        ...         },
        ...         default="db.t3.micro",
        ...     )

    Args:
        value: Value to match (or callable(context) -> value)
        cases: Dict mapping values to results
        default: Default value if no case matches

    Returns:
        A conditional value that resolves at serialization time
    """
    return MatchCondition(value=value, cases=cases, default=default)  # type: ignore[return-value]
