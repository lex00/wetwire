"""Domain-specific testing configurations.

Each domain package (wetwire-aws, wetwire-gcp, etc.) has a corresponding
module here with domain-specific prompts and runner configuration.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wetwire_agent.domains.aws import AwsDomain

__all__ = ["get_domain", "list_domains"]

# Available domains - lazy loaded
_DOMAINS = {
    "aws": "wetwire_agent.domains.aws",
}


def list_domains() -> list[str]:
    """List available domain names."""
    return list(_DOMAINS.keys())


def get_domain(name: str) -> "AwsDomain":
    """Get a domain by name.

    Args:
        name: Domain name (e.g., "aws")

    Returns:
        Domain configuration object

    Raises:
        ValueError: If domain is not available
    """
    if name not in _DOMAINS:
        valid = ", ".join(_DOMAINS.keys())
        raise ValueError(f"Unknown domain '{name}'. Available: {valid}")

    if name == "aws":
        from wetwire_agent.domains.aws import AwsDomain

        return AwsDomain()

    raise ValueError(f"Domain '{name}' not yet implemented")
