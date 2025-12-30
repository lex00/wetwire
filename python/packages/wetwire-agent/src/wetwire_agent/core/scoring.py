"""Scoring rubric implementation.

Each session is scored on 5 dimensions (0-3 scale):

| Dimension           | 0                    | 1                  | 2                  | 3                  |
|---------------------|----------------------|--------------------|--------------------|--------------------|
| Completeness        | Failed to produce    | Missing resources  | Most resources     | All resources      |
| Lint Quality        | Never passed         | Passed after 3     | Passed after 1-2   | Passed first try   |
| Code Quality        | Invalid syntax       | Poor patterns      | Good patterns      | Idiomatic          |
| Output Validity     | Invalid              | Valid with errors  | Valid with warnings| Clean              |
| Question Efficiency | 5+ questions         | 3-4 questions      | 1-2 questions      | 0 (when appropriate)|

Overall Score: 0-15
- 0-5: Failure
- 6-9: Partial success
- 10-12: Success
- 13-15: Excellent
"""

from dataclasses import dataclass
from enum import IntEnum


class Rating(IntEnum):
    """Individual dimension rating (0-3)."""

    NONE = 0
    POOR = 1
    GOOD = 2
    EXCELLENT = 3


@dataclass
class Score:
    """Complete session score.

    Attributes:
        completeness: Did the session produce a valid package?
        lint_quality: How many lint cycles were needed?
        code_quality: Is the code idiomatic and well-structured?
        output_validity: Does the output validate successfully?
        question_efficiency: How many clarification questions were asked?
    """

    completeness: Rating
    lint_quality: Rating
    code_quality: Rating
    output_validity: Rating
    question_efficiency: Rating

    @property
    def total(self) -> int:
        """Calculate total score (0-15)."""
        return (
            self.completeness
            + self.lint_quality
            + self.code_quality
            + self.output_validity
            + self.question_efficiency
        )

    @property
    def grade(self) -> str:
        """Get letter grade based on total score."""
        total = self.total
        if total >= 13:
            return "Excellent"
        elif total >= 10:
            return "Success"
        elif total >= 6:
            return "Partial"
        else:
            return "Failure"

    @property
    def passed(self) -> bool:
        """Check if the score passes CI/CD threshold (>= 6)."""
        return self.total >= 6


def score_completeness(produced_package: bool, missing_resources: int, total_resources: int) -> Rating:
    """Score completeness dimension.

    Args:
        produced_package: Was a package produced at all?
        missing_resources: Number of missing resources
        total_resources: Total expected resources

    Returns:
        Rating for completeness
    """
    if not produced_package:
        return Rating.NONE
    if missing_resources == 0:
        return Rating.EXCELLENT
    if missing_resources < total_resources // 2:
        return Rating.GOOD
    return Rating.POOR


def score_lint_quality(cycles: int, passed: bool) -> Rating:
    """Score lint quality dimension.

    Args:
        cycles: Number of lint cycles taken
        passed: Did lint eventually pass?

    Returns:
        Rating for lint quality
    """
    if not passed:
        return Rating.NONE
    if cycles == 0:
        return Rating.EXCELLENT
    if cycles <= 2:
        return Rating.GOOD
    return Rating.POOR


def score_code_quality(syntax_valid: bool, pattern_issues: int) -> Rating:
    """Score code quality dimension.

    Args:
        syntax_valid: Is the code syntactically valid?
        pattern_issues: Number of pattern/style issues

    Returns:
        Rating for code quality
    """
    if not syntax_valid:
        return Rating.NONE
    if pattern_issues == 0:
        return Rating.EXCELLENT
    if pattern_issues <= 2:
        return Rating.GOOD
    return Rating.POOR


def score_output_validity(valid: bool, errors: int, warnings: int) -> Rating:
    """Score output validity dimension.

    Args:
        valid: Is the output structurally valid?
        errors: Number of validation errors
        warnings: Number of validation warnings

    Returns:
        Rating for output validity
    """
    if not valid:
        return Rating.NONE
    if errors == 0 and warnings == 0:
        return Rating.EXCELLENT
    if errors == 0:
        return Rating.GOOD
    return Rating.POOR


def score_question_efficiency(questions: int, appropriate_questions: int) -> Rating:
    """Score question efficiency dimension.

    Args:
        questions: Total questions asked
        appropriate_questions: Questions that were truly necessary

    Returns:
        Rating for question efficiency
    """
    # If no questions needed and none asked, that's excellent
    if appropriate_questions == 0 and questions == 0:
        return Rating.EXCELLENT
    if questions <= 2:
        return Rating.GOOD
    if questions <= 4:
        return Rating.POOR
    return Rating.NONE


def calculate_score(
    produced_package: bool,
    missing_resources: int,
    total_resources: int,
    lint_cycles: int,
    lint_passed: bool,
    syntax_valid: bool,
    pattern_issues: int,
    output_valid: bool,
    validation_errors: int,
    validation_warnings: int,
    questions_asked: int,
    appropriate_questions: int,
) -> Score:
    """Calculate complete session score.

    Args:
        produced_package: Was a package produced?
        missing_resources: Number of missing resources
        total_resources: Total expected resources
        lint_cycles: Number of lint cycles
        lint_passed: Did lint pass?
        syntax_valid: Is code syntactically valid?
        pattern_issues: Number of pattern issues
        output_valid: Is output valid?
        validation_errors: Number of validation errors
        validation_warnings: Number of validation warnings
        questions_asked: Total questions asked
        appropriate_questions: Truly necessary questions

    Returns:
        Complete Score object
    """
    return Score(
        completeness=score_completeness(produced_package, missing_resources, total_resources),
        lint_quality=score_lint_quality(lint_cycles, lint_passed),
        code_quality=score_code_quality(syntax_valid, pattern_issues),
        output_validity=score_output_validity(output_valid, validation_errors, validation_warnings),
        question_efficiency=score_question_efficiency(questions_asked, appropriate_questions),
    )
