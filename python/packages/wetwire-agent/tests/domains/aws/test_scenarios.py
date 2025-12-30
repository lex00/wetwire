"""Tests for AWS agent scenarios.

Each scenario contains:
- prompts/<persona>.md: Persona-specific prompts (beginner, intermediate, expert, terse, verbose)
- expected/: The reference package that should pass validation
- results/<persona>/: Generated results per persona (score.json, results.md, template.yaml)

Tests validate that the expected output still works (lint, build).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
PERSONAS = ["beginner", "intermediate", "expert", "terse", "verbose"]


def get_scenarios():
    """Discover all scenario directories."""
    if not SCENARIOS_DIR.exists():
        return []
    return [d.name for d in SCENARIOS_DIR.iterdir() if d.is_dir() and (d / "expected").exists()]


@pytest.mark.parametrize("scenario", get_scenarios())
class TestScenarioValidation:
    """Validate that committed scenario code still works."""

    def test_expected_lints_clean(self, scenario):
        """Expected output passes wetwire-aws lint."""
        expected_dir = SCENARIOS_DIR / scenario / "expected"

        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "lint", str(expected_dir)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Lint failed:\n{result.stdout}\n{result.stderr}"

    def test_expected_builds(self, scenario):
        """Expected output builds a valid CloudFormation template."""
        expected_dir = SCENARIOS_DIR / scenario / "expected"

        # Get the module name from the directory structure
        module_name = expected_dir.name

        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "build", "-m", module_name],
            capture_output=True,
            text=True,
            env={**dict(__import__("os").environ), "PYTHONPATH": str(expected_dir.parent)},
        )
        assert result.returncode == 0, f"Build failed:\n{result.stdout}\n{result.stderr}"
        assert "AWS::" in result.stdout, "No AWS resources in output"

    def test_has_prompts(self, scenario):
        """Scenario has persona-specific prompts."""
        prompts_dir = SCENARIOS_DIR / scenario / "prompts"
        assert prompts_dir.exists(), f"Missing prompts/ directory for {scenario}"

        # At least one persona prompt must exist
        persona_prompts = list(prompts_dir.glob("*.md"))
        assert persona_prompts, f"No persona prompts in {prompts_dir}"

        # Verify each prompt has content
        for prompt_file in persona_prompts:
            assert prompt_file.read_text().strip(), f"{prompt_file.name} is empty"

    def test_has_results_for_run_personas(self, scenario):
        """Scenario has results for at least one persona (if results exist)."""
        results_dir = SCENARIOS_DIR / scenario / "results"

        # Results are optional - only validate if present
        if not results_dir.exists():
            pytest.skip("No results directory (run --save-results to generate)")

        persona_dirs = [d for d in results_dir.iterdir() if d.is_dir()]
        assert persona_dirs, f"No persona results in {results_dir}"

        for persona_dir in persona_dirs:
            # Each persona result should have score.json
            score_file = persona_dir / "score.json"
            if score_file.exists():
                score = json.loads(score_file.read_text())
                assert "total" in score, f"{persona_dir.name}/score.json missing 'total'"
                assert "max" in score, f"{persona_dir.name}/score.json missing 'max'"

            # Results.md is optional but should have content if present
            results_file = persona_dir / "results.md"
            if results_file.exists():
                content = results_file.read_text()
                assert "Score" in content or "score" in content, (
                    f"{persona_dir.name}/results.md missing score info"
                )
