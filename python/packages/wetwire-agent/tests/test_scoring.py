"""Tests for scoring module."""

import pytest

from wetwire_agent.core.scoring import (
    Rating,
    Score,
    calculate_score,
    score_completeness,
    score_lint_quality,
)


def test_rating_values():
    """Test Rating enum values."""
    assert Rating.NONE == 0
    assert Rating.POOR == 1
    assert Rating.GOOD == 2
    assert Rating.EXCELLENT == 3


def test_score_total():
    """Test Score.total calculation."""
    score = Score(
        completeness=Rating.EXCELLENT,
        lint_quality=Rating.EXCELLENT,
        code_quality=Rating.EXCELLENT,
        output_validity=Rating.EXCELLENT,
        question_efficiency=Rating.EXCELLENT,
    )
    assert score.total == 15


def test_score_grade_excellent():
    """Test excellent grade threshold."""
    score = Score(
        completeness=Rating.EXCELLENT,
        lint_quality=Rating.EXCELLENT,
        code_quality=Rating.EXCELLENT,
        output_validity=Rating.EXCELLENT,
        question_efficiency=Rating.GOOD,  # 14 total
    )
    assert score.grade == "Excellent"
    assert score.passed


def test_score_grade_failure():
    """Test failure grade threshold."""
    score = Score(
        completeness=Rating.NONE,
        lint_quality=Rating.NONE,
        code_quality=Rating.NONE,
        output_validity=Rating.POOR,
        question_efficiency=Rating.POOR,  # 2 total
    )
    assert score.grade == "Failure"
    assert not score.passed


def test_score_completeness():
    """Test completeness scoring."""
    # No package
    assert score_completeness(False, 0, 5) == Rating.NONE
    # All resources
    assert score_completeness(True, 0, 5) == Rating.EXCELLENT
    # Missing some
    assert score_completeness(True, 1, 5) == Rating.GOOD
    # Missing most
    assert score_completeness(True, 4, 5) == Rating.POOR


def test_score_lint_quality():
    """Test lint quality scoring."""
    # Never passed
    assert score_lint_quality(3, False) == Rating.NONE
    # Passed first try
    assert score_lint_quality(0, True) == Rating.EXCELLENT
    # Passed after 1-2 cycles
    assert score_lint_quality(2, True) == Rating.GOOD
    # Passed after 3 cycles
    assert score_lint_quality(3, True) == Rating.POOR


def test_calculate_score():
    """Test full score calculation."""
    score = calculate_score(
        produced_package=True,
        missing_resources=0,
        total_resources=5,
        lint_cycles=1,
        lint_passed=True,
        syntax_valid=True,
        pattern_issues=0,
        output_valid=True,
        validation_errors=0,
        validation_warnings=0,
        questions_asked=1,
        appropriate_questions=1,
    )
    assert score.total >= 10
    assert score.grade in ("Success", "Excellent")
