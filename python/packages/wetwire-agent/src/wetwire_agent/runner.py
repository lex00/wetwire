"""Scenario runner for wetwire-agent.

This module orchestrates running a scenario:
1. Load prompt and persona
2. Run Developer <-> Runner conversation
3. Generate package
4. Run wetwire-aws lint
5. Build CloudFormation template
6. Run cfn-lint on generated template
7. Score results
8. Generate results.md

The conversation can be:
- Simulated (for testing) - uses predefined responses
- Live (for production) - uses AI API calls
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol


@dataclass
class Message:
    """A message in the conversation."""
    role: str  # "developer" or "runner"
    content: str


@dataclass
class LintResult:
    """Result of running the wetwire-aws linter."""
    passed: bool
    issues: list[str] = field(default_factory=list)


@dataclass
class BuildResult:
    """Result of building the CloudFormation template."""
    success: bool
    template: str = ""
    template_path: Path | None = None
    error: str = ""


@dataclass
class CfnLintResult:
    """Result of running cfn-lint on the generated template."""
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    informational: list[str] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        return len(self.errors) + len(self.warnings) + len(self.informational)


@dataclass
class ScoreResult:
    """Scoring breakdown."""
    completeness: int = 0
    lint_quality: int = 0
    code_quality: int = 0
    output_validity: int = 0
    question_efficiency: int = 0

    @property
    def total(self) -> int:
        return (self.completeness + self.lint_quality + self.code_quality +
                self.output_validity + self.question_efficiency)

    @property
    def max(self) -> int:
        return 15

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "max": self.max,
            "dimensions": {
                "completeness": {"score": self.completeness, "max": 3},
                "lint_quality": {"score": self.lint_quality, "max": 3},
                "code_quality": {"score": self.code_quality, "max": 3},
                "output_validity": {"score": self.output_validity, "max": 3},
                "question_efficiency": {"score": self.question_efficiency, "max": 3},
            }
        }


@dataclass
class ScenarioResult:
    """Complete result of running a scenario."""
    prompt: str
    persona: str
    package_path: Path
    conversation: list[Message]
    lint_cycles: list[LintResult]
    build_result: BuildResult
    cfn_lint_result: CfnLintResult
    score: ScoreResult
    framework_issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class ConversationHandler(Protocol):
    """Protocol for handling Developer <-> Runner conversation."""

    def get_developer_response(self, runner_message: str) -> str:
        """Get the Developer's response to a Runner message."""
        ...

    def get_runner_response(self, developer_message: str) -> str:
        """Get the Runner's response to a Developer message."""
        ...


class ScenarioRunner:
    """Runs a scenario end-to-end."""

    def __init__(
        self,
        scenario_dir: Path,
        output_dir: Path | None = None,
        conversation_handler: ConversationHandler | None = None,
        persona: str = "beginner",
    ):
        self.scenario_dir = scenario_dir
        self.output_dir = output_dir or Path(tempfile.mkdtemp(prefix="wetwire-scenario-"))
        self.conversation_handler = conversation_handler
        self.persona = persona
        self.conversation: list[Message] = []
        self.lint_cycles: list[LintResult] = []

    def load_prompt(self) -> str:
        """Load the prompt for the current persona.

        Looks for prompts/<persona>.md first, falls back to prompt.md for
        backwards compatibility.
        """
        # Try persona-specific prompt first
        persona_prompt = self.scenario_dir / "prompts" / f"{self.persona}.md"
        if persona_prompt.exists():
            return persona_prompt.read_text().strip()

        # Fall back to legacy prompt.md
        prompt_file = self.scenario_dir / "prompt.md"
        if prompt_file.exists():
            return prompt_file.read_text().strip()

        raise FileNotFoundError(
            f"No prompt found for persona '{self.persona}'. "
            f"Expected: {persona_prompt} or {prompt_file}"
        )

    def run_lint(self, package_path: Path) -> LintResult:
        """Run wetwire-aws lint on the package."""
        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "lint", str(package_path)],
            capture_output=True,
            text=True,
        )

        issues = []
        if result.returncode != 0:
            # Parse issues from stdout
            for line in result.stdout.split("\n"):
                if ": WAW" in line:
                    issues.append(line.strip())

        return LintResult(passed=result.returncode == 0, issues=issues)

    def run_build(self, package_path: Path, module_name: str) -> BuildResult:
        """Run wetwire-aws build on the package and save template."""
        import os

        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "build", "-m", module_name, "-f", "yaml"],
            capture_output=True,
            text=True,
            env={**dict(os.environ), "PYTHONPATH": str(package_path.parent)},
        )

        if result.returncode == 0:
            # Save template to file for cfn-lint
            template_path = self.output_dir / f"{module_name}.yaml"
            template_path.write_text(result.stdout)
            return BuildResult(
                success=True,
                template=result.stdout,
                template_path=template_path,
            )
        else:
            return BuildResult(success=False, error=result.stderr)

    def run_cfn_lint(self, template_path: Path) -> CfnLintResult:
        """Run cfn-lint on the generated CloudFormation template."""
        result = subprocess.run(
            [sys.executable, "-m", "cfnlint", str(template_path), "-f", "json"],
            capture_output=True,
            text=True,
        )

        errors: list[str] = []
        warnings: list[str] = []
        informational: list[str] = []

        if result.stdout.strip():
            try:
                issues = json.loads(result.stdout)
                for issue in issues:
                    level = issue.get("Level", "Error")
                    rule = issue.get("Rule", {}).get("Id", "Unknown")
                    message = issue.get("Message", "No message")
                    location = issue.get("Location", {})
                    path = location.get("Path", [])
                    path_str = "/".join(str(p) for p in path) if path else ""

                    formatted = f"{rule}: {message}"
                    if path_str:
                        formatted += f" (at {path_str})"

                    if level == "Error":
                        errors.append(formatted)
                    elif level == "Warning":
                        warnings.append(formatted)
                    else:
                        informational.append(formatted)
            except json.JSONDecodeError:
                # Fall back to raw output parsing
                for line in result.stdout.split("\n"):
                    line = line.strip()
                    if line:
                        if ":E" in line or "error" in line.lower():
                            errors.append(line)
                        elif ":W" in line or "warning" in line.lower():
                            warnings.append(line)
                        else:
                            informational.append(line)

        passed = len(errors) == 0
        return CfnLintResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            informational=informational,
        )

    def calculate_score(
        self,
        lint_cycles: list[LintResult],
        build_result: BuildResult,
        cfn_lint_result: CfnLintResult,
        num_questions: int,
    ) -> ScoreResult:
        """Calculate the score based on results."""
        score = ScoreResult()

        # Completeness: Did we produce a valid package?
        if build_result.success and "AWS::" in build_result.template:
            score.completeness = 3
        elif build_result.success:
            score.completeness = 2
        else:
            score.completeness = 0

        # Lint quality: How many cycles to pass?
        if lint_cycles and lint_cycles[0].passed:
            score.lint_quality = 3  # Passed first try
        elif len(lint_cycles) <= 2 and any(c.passed for c in lint_cycles):
            score.lint_quality = 2  # Passed in 1-2 cycles
        elif any(c.passed for c in lint_cycles):
            score.lint_quality = 1  # Passed after 3 cycles
        else:
            score.lint_quality = 0  # Never passed

        # Code quality: Based on wetwire-aws lint + cfn-lint
        if any(c.passed for c in lint_cycles):
            if cfn_lint_result.passed and len(cfn_lint_result.warnings) == 0:
                score.code_quality = 3  # Clean on both linters
            elif cfn_lint_result.passed:
                score.code_quality = 2  # Errors-free but has warnings
            else:
                score.code_quality = 1  # Has cfn-lint errors
        else:
            score.code_quality = 0

        # Output validity: cfn-lint is the authority
        if cfn_lint_result.passed and len(cfn_lint_result.warnings) == 0:
            score.output_validity = 3
        elif cfn_lint_result.passed:
            score.output_validity = 2
        elif build_result.success:
            score.output_validity = 1  # Builds but cfn-lint fails
        else:
            score.output_validity = 0

        # Question efficiency
        if num_questions == 0:
            score.question_efficiency = 3
        elif num_questions <= 2:
            score.question_efficiency = 3
        elif num_questions <= 4:
            score.question_efficiency = 2
        else:
            score.question_efficiency = 1

        return score

    def generate_results_md(self, result: ScenarioResult) -> str:
        """Generate the results.md content."""
        lines = [
            "# Package Generation Results",
            "",
            f"**Prompt:** \"{result.prompt}\"",
            f"**Package:** {result.package_path.name}",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d')}",
            f"**Persona:** {result.persona}",
            "",
            "## Summary",
            "",
            f"Created package at: {result.package_path}",
            "",
        ]

        # Build status
        if result.build_result.success:
            lines.append(f"Template generated: {result.build_result.template_path}")
        else:
            lines.append(f"Build failed: {result.build_result.error}")
        lines.append("")

        # wetwire-aws Lint section
        lines.extend([
            "## wetwire-aws Lint",
            "",
        ])

        for i, cycle in enumerate(result.lint_cycles, 1):
            lines.append(f"### Cycle {i}")
            lines.append(f"**Status:** {'PASS' if cycle.passed else 'FAIL'}")
            lines.append(f"**Issues Found:** {len(cycle.issues)}")
            if cycle.issues:
                for issue in cycle.issues:
                    lines.append(f"- {issue}")
            else:
                lines.append("- All lint checks passed")
            lines.append("")

        # cfn-lint section
        lines.extend([
            "## cfn-lint Validation",
            "",
            f"**Status:** {'PASS' if result.cfn_lint_result.passed else 'FAIL'}",
            f"**Errors:** {len(result.cfn_lint_result.errors)}",
            f"**Warnings:** {len(result.cfn_lint_result.warnings)}",
            f"**Info:** {len(result.cfn_lint_result.informational)}",
            "",
        ])

        if result.cfn_lint_result.errors:
            lines.append("### Errors")
            for error in result.cfn_lint_result.errors:
                lines.append(f"- {error}")
            lines.append("")

        if result.cfn_lint_result.warnings:
            lines.append("### Warnings")
            for warning in result.cfn_lint_result.warnings:
                lines.append(f"- {warning}")
            lines.append("")

        if result.cfn_lint_result.informational:
            lines.append("### Informational")
            for info in result.cfn_lint_result.informational:
                lines.append(f"- {info}")
            lines.append("")

        if result.cfn_lint_result.total_issues == 0:
            lines.append("All cfn-lint checks passed.")
            lines.append("")

        # Conversation log (only if there's actual back-and-forth)
        if len(result.conversation) > 1:
            lines.extend([
                "## Conversation Log",
                "",
                "```",
            ])

            for msg in result.conversation:
                role = "Developer" if msg.role == "developer" else "Runner"
                lines.append(f"{role}: {msg.content}")
                lines.append("")

            lines.extend([
                "```",
                "",
            ])

        lines.extend([
            "## Score Breakdown",
            "",
            "| Dimension | Score | Max |",
            "|-----------|-------|-----|",
            f"| Completeness | {result.score.completeness} | 3 |",
            f"| Lint Quality | {result.score.lint_quality} | 3 |",
            f"| Code Quality | {result.score.code_quality} | 3 |",
            f"| Output Validity | {result.score.output_validity} | 3 |",
            f"| Question Efficiency | {result.score.question_efficiency} | 3 |",
            "",
            f"**Total: {result.score.total}/{result.score.max}**",
            "",
        ])

        if result.framework_issues:
            lines.extend([
                "## Framework Issues Found",
                "",
            ])
            for issue in result.framework_issues:
                lines.append(f"- {issue}")
            lines.append("")

        if result.suggestions:
            lines.extend([
                "## Framework Improvement Suggestions",
                "",
            ])
            for suggestion in result.suggestions:
                lines.append(f"- {suggestion}")
            lines.append("")

        return "\n".join(lines)

    def run(self) -> ScenarioResult:
        """Run the full scenario."""
        prompt = self.load_prompt()
        persona = self.persona

        # Initialize conversation with prompt
        self.conversation.append(Message(role="developer", content=prompt))

        # For now, copy expected output if it exists (simulation mode)
        expected_dir = self.scenario_dir / "expected"
        package_path = self.output_dir / expected_dir.name

        if expected_dir.exists():
            import shutil
            if package_path.exists():
                shutil.rmtree(package_path)
            shutil.copytree(expected_dir, package_path)

        # Run wetwire-aws lint
        lint_result = self.run_lint(package_path)
        self.lint_cycles.append(lint_result)

        # Run build to generate CloudFormation template
        build_result = self.run_build(package_path, package_path.name)

        # Run cfn-lint on generated template
        if build_result.success and build_result.template_path:
            cfn_lint_result = self.run_cfn_lint(build_result.template_path)
        else:
            cfn_lint_result = CfnLintResult(
                passed=False,
                errors=["Build failed - no template to validate"],
            )

        # Count questions (messages from runner that end with ?)
        num_questions = sum(
            1 for msg in self.conversation
            if msg.role == "runner" and "?" in msg.content
        )

        # Calculate score
        score = self.calculate_score(
            self.lint_cycles,
            build_result,
            cfn_lint_result,
            num_questions,
        )

        result = ScenarioResult(
            prompt=prompt,
            persona=persona,
            package_path=package_path,
            conversation=self.conversation,
            lint_cycles=self.lint_cycles,
            build_result=build_result,
            cfn_lint_result=cfn_lint_result,
            score=score,
        )

        return result


def run_scenario(scenario_dir: Path, output_dir: Path | None = None) -> ScenarioResult:
    """Convenience function to run a scenario."""
    runner = ScenarioRunner(scenario_dir, output_dir)
    return runner.run()
