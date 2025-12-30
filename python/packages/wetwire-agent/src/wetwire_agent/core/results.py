"""RESULTS.md writer for session documentation.

Every session produces a RESULTS.md documenting the process:

- Summary of what was created
- Lint cycles with issues and actions
- Questions asked during the session
- Framework improvement suggestions
- Final score
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from wetwire_agent.core.scoring import Score


@dataclass
class LintCycle:
    """Documentation for a single lint cycle."""

    cycle_number: int
    issues_found: int
    issues: list[str]
    actions_taken: list[str]


@dataclass
class Question:
    """Documentation for a clarification question."""

    runner_question: str
    developer_response: str


@dataclass
class SessionResults:
    """Complete results from an orchestration session.

    Attributes:
        prompt: The initial user prompt
        package_name: Name of the generated package
        domain: The domain used (aws, gcp, etc.)
        persona: Persona name (for testing) or None
        summary: Summary of what was created
        lint_cycles: Documentation of each lint cycle
        questions: Questions asked during the session
        suggestions: Framework improvement suggestions
        score: Final session score
        started_at: When the session started
        completed_at: When the session completed
    """

    prompt: str
    package_name: str
    domain: str
    persona: str | None = None
    summary: str = ""
    lint_cycles: list[LintCycle] = field(default_factory=list)
    questions: list[Question] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    score: Score | None = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None


class ResultsWriter:
    """Writer for RESULTS.md files.

    Example:
        >>> results = SessionResults(
        ...     prompt="Create a VPC with subnets",
        ...     package_name="my_vpc",
        ...     domain="aws",
        ... )
        >>> writer = ResultsWriter()
        >>> writer.write(results, Path("output/RESULTS.md"))
    """

    def format(self, results: SessionResults) -> str:
        """Format results as markdown.

        Args:
            results: The session results to format

        Returns:
            Formatted markdown string
        """
        lines = [
            "# Package Generation Results",
            "",
            f"**Prompt:** \"{results.prompt}\"",
            f"**Package:** {results.package_name}",
            f"**Domain:** {results.domain}",
            f"**Date:** {results.started_at.strftime('%Y-%m-%d')}",
        ]

        if results.persona:
            lines.append(f"**Persona:** {results.persona}")

        lines.extend(["", "## Summary", "", results.summary or "_No summary provided_", ""])

        # Lint cycles
        lines.append("## Lint Cycles")
        lines.append("")
        if results.lint_cycles:
            for cycle in results.lint_cycles:
                lines.append(f"### Cycle {cycle.cycle_number}")
                lines.append(f"**Issues Found:** {cycle.issues_found}")
                if cycle.issues:
                    for issue in cycle.issues:
                        lines.append(f"- {issue}")
                lines.append("")
                if cycle.actions_taken:
                    lines.append("**Actions Taken:**")
                    for action in cycle.actions_taken:
                        lines.append(f"- {action}")
                lines.append("")
        else:
            lines.append("_No lint cycles needed_")
            lines.append("")

        # Questions
        lines.append("## Questions Asked")
        lines.append("")
        if results.questions:
            for i, q in enumerate(results.questions, 1):
                lines.append(f"{i}. **Runner:** \"{q.runner_question}\"")
                lines.append(f"   **Developer:** \"{q.developer_response}\"")
                lines.append("")
        else:
            lines.append("_No questions asked_")
            lines.append("")

        # Suggestions
        if results.suggestions:
            lines.append("## Framework Improvement Suggestions")
            lines.append("")
            for i, suggestion in enumerate(results.suggestions, 1):
                lines.append(f"{i}. {suggestion}")
            lines.append("")

        # Score
        if results.score:
            lines.append("## Score")
            lines.append("")
            lines.append(f"| Dimension | Score |")
            lines.append(f"|-----------|-------|")
            lines.append(f"| Completeness | {results.score.completeness}/3 |")
            lines.append(f"| Lint Quality | {results.score.lint_quality}/3 |")
            lines.append(f"| Code Quality | {results.score.code_quality}/3 |")
            lines.append(f"| Output Validity | {results.score.output_validity}/3 |")
            lines.append(f"| Question Efficiency | {results.score.question_efficiency}/3 |")
            lines.append(f"| **Total** | **{results.score.total}/15** |")
            lines.append("")
            lines.append(f"**Grade:** {results.score.grade}")
            lines.append("")

        return "\n".join(lines)

    def write(self, results: SessionResults, path: Path) -> None:
        """Write results to a file.

        Args:
            results: The session results to write
            path: Path to write the RESULTS.md file
        """
        content = self.format(results)
        path.write_text(content)
