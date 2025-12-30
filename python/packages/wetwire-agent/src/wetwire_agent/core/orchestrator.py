"""Orchestrator for Developer/Runner communication.

The orchestrator coordinates communication between the Developer (human or AI)
and the Runner (AI with CLI tools). It handles:

- Message routing between Developer and Runner
- Maximum cycle enforcement (default: 3 lint cycles)
- Session state management
- Final output collection
"""

from dataclasses import dataclass, field
from typing import Protocol, Any


class DeveloperProtocol(Protocol):
    """Protocol for Developer role (human or AI)."""

    def respond(self, message: str) -> str:
        """Respond to a message from the Runner."""
        ...


class RunnerProtocol(Protocol):
    """Protocol for Runner role (AI with CLI tools)."""

    def process(self, message: str) -> str:
        """Process a message and return response or question."""
        ...

    def is_complete(self) -> bool:
        """Check if the Runner has completed its work."""
        ...


@dataclass
class SessionConfig:
    """Configuration for an orchestration session."""

    domain: str
    max_lint_cycles: int = 3
    output_dir: str | None = None


@dataclass
class Session:
    """Represents an orchestration session."""

    config: SessionConfig
    messages: list[dict[str, Any]] = field(default_factory=list)
    lint_cycles: int = 0
    complete: bool = False
    score: int | None = None


class Orchestrator:
    """Coordinates Developer/Runner communication.

    The orchestrator manages the back-and-forth between Developer and Runner,
    enforcing constraints like maximum lint cycles and collecting outputs.

    Example:
        >>> orchestrator = Orchestrator()
        >>> session = orchestrator.create_session(
        ...     domain="aws",
        ...     developer=ai_developer,
        ...     runner=ai_runner,
        ... )
        >>> result = orchestrator.run(session, initial_prompt="Create a VPC")
    """

    def __init__(self) -> None:
        """Initialize the orchestrator."""
        pass

    def create_session(
        self,
        domain: str,
        developer: DeveloperProtocol,
        runner: RunnerProtocol,
        max_lint_cycles: int = 3,
    ) -> Session:
        """Create a new orchestration session.

        Args:
            domain: The domain to use (e.g., "aws", "gcp")
            developer: The Developer role implementation
            runner: The Runner role implementation
            max_lint_cycles: Maximum number of lint cycles allowed

        Returns:
            A new Session object
        """
        config = SessionConfig(domain=domain, max_lint_cycles=max_lint_cycles)
        return Session(config=config)

    def run(self, session: Session, initial_prompt: str) -> dict[str, Any]:
        """Run an orchestration session.

        Args:
            session: The session to run
            initial_prompt: The initial prompt from the Developer

        Returns:
            Result dictionary with package path, score, and metadata
        """
        # TODO: Implement orchestration loop
        raise NotImplementedError("Orchestrator.run() not yet implemented")
