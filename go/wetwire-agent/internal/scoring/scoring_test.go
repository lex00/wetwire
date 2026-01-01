package scoring

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestRating_String(t *testing.T) {
	tests := []struct {
		rating   Rating
		contains string
	}{
		{RatingNone, "None"},
		{RatingPartial, "Partial"},
		{RatingGood, "Good"},
		{RatingExcellent, "Excellent"},
	}

	for _, tt := range tests {
		t.Run(tt.contains, func(t *testing.T) {
			assert.Contains(t, tt.rating.String(), tt.contains)
		})
	}
}

func TestScore_Total(t *testing.T) {
	s := NewScore("test", "test")
	assert.Equal(t, 0, s.Total())

	s.Completeness.Rating = RatingExcellent
	s.LintQuality.Rating = RatingExcellent
	s.CodeQuality.Rating = RatingExcellent
	s.OutputValidity.Rating = RatingExcellent
	s.QuestionEfficiency.Rating = RatingExcellent
	assert.Equal(t, 15, s.Total())

	s.Completeness.Rating = RatingGood
	s.LintQuality.Rating = RatingGood
	s.CodeQuality.Rating = RatingGood
	s.OutputValidity.Rating = RatingGood
	s.QuestionEfficiency.Rating = RatingGood
	assert.Equal(t, 10, s.Total())
}

func TestScore_Threshold(t *testing.T) {
	tests := []struct {
		total    int
		expected string
	}{
		{15, "Excellent"},
		{13, "Excellent"},
		{12, "Success"},
		{10, "Success"},
		{9, "Partial"},
		{6, "Partial"},
		{5, "Failure"},
		{0, "Failure"},
	}

	for _, tt := range tests {
		t.Run(tt.expected, func(t *testing.T) {
			s := NewScore("test", "test")
			// Set ratings to achieve the target total
			s.Completeness.Rating = Rating(tt.total / 5)
			s.LintQuality.Rating = Rating(tt.total / 5)
			s.CodeQuality.Rating = Rating(tt.total / 5)
			s.OutputValidity.Rating = Rating(tt.total / 5)
			s.QuestionEfficiency.Rating = Rating(tt.total - (4 * (tt.total / 5)))

			assert.Equal(t, tt.expected, s.Threshold())
		})
	}
}

func TestScore_Passed(t *testing.T) {
	s := NewScore("test", "test")
	assert.False(t, s.Passed())

	// Set to exactly 6
	s.Completeness.Rating = RatingGood
	s.LintQuality.Rating = RatingGood
	s.CodeQuality.Rating = RatingGood
	assert.True(t, s.Passed())
}

func TestScoreCompleteness(t *testing.T) {
	tests := []struct {
		expected int
		actual   int
		rating   Rating
	}{
		{10, 10, RatingExcellent},
		{10, 9, RatingGood},
		{10, 8, RatingGood},
		{10, 5, RatingPartial},
		{10, 3, RatingNone},
		{0, 0, RatingExcellent},
	}

	for _, tt := range tests {
		rating, _ := ScoreCompleteness(tt.expected, tt.actual)
		assert.Equal(t, tt.rating, rating, "expected=%d, actual=%d", tt.expected, tt.actual)
	}
}

func TestScoreLintQuality(t *testing.T) {
	tests := []struct {
		cycles int
		passed bool
		rating Rating
	}{
		{1, true, RatingExcellent},
		{0, true, RatingExcellent},
		{2, true, RatingGood},
		{3, true, RatingPartial},
		{5, true, RatingPartial},
		{1, false, RatingNone},
		{3, false, RatingNone},
	}

	for _, tt := range tests {
		rating, _ := ScoreLintQuality(tt.cycles, tt.passed)
		assert.Equal(t, tt.rating, rating, "cycles=%d, passed=%v", tt.cycles, tt.passed)
	}
}

func TestScoreCodeQuality(t *testing.T) {
	tests := []struct {
		issues []string
		rating Rating
	}{
		{nil, RatingExcellent},
		{[]string{}, RatingExcellent},
		{[]string{"issue1"}, RatingGood},
		{[]string{"issue1", "issue2"}, RatingGood},
		{[]string{"1", "2", "3"}, RatingPartial},
		{[]string{"1", "2", "3", "4", "5", "6"}, RatingNone},
	}

	for _, tt := range tests {
		rating, _ := ScoreCodeQuality(tt.issues)
		assert.Equal(t, tt.rating, rating, "issues=%d", len(tt.issues))
	}
}

func TestScoreOutputValidity(t *testing.T) {
	tests := []struct {
		errors   int
		warnings int
		rating   Rating
	}{
		{0, 0, RatingExcellent},
		{0, 1, RatingGood},
		{0, 2, RatingGood},
		{0, 5, RatingPartial},
		{1, 0, RatingNone},
		{5, 10, RatingNone},
	}

	for _, tt := range tests {
		rating, _ := ScoreOutputValidity(tt.errors, tt.warnings)
		assert.Equal(t, tt.rating, rating, "errors=%d, warnings=%d", tt.errors, tt.warnings)
	}
}

func TestScoreQuestionEfficiency(t *testing.T) {
	tests := []struct {
		questions int
		rating    Rating
	}{
		{0, RatingExcellent},
		{2, RatingExcellent},
		{3, RatingGood},
		{4, RatingGood},
		{5, RatingPartial},
		{6, RatingPartial},
		{7, RatingNone},
		{10, RatingNone},
	}

	for _, tt := range tests {
		rating, _ := ScoreQuestionEfficiency(tt.questions)
		assert.Equal(t, tt.rating, rating, "questions=%d", tt.questions)
	}
}

func TestScore_String(t *testing.T) {
	s := NewScore("beginner", "s3_bucket")
	s.Completeness.Rating = RatingExcellent
	s.Completeness.Notes = "All resources"
	s.LintQuality.Rating = RatingGood
	s.CodeQuality.Rating = RatingGood
	s.OutputValidity.Rating = RatingExcellent
	s.QuestionEfficiency.Rating = RatingExcellent

	str := s.String()
	assert.Contains(t, str, "13/15")
	assert.Contains(t, str, "Excellent")
	assert.Contains(t, str, "beginner")
	assert.Contains(t, str, "s3_bucket")
	assert.Contains(t, str, "Completeness")
}
