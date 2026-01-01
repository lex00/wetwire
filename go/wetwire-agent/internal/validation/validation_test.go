package validation

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestCfnLintResult_TotalIssues(t *testing.T) {
	tests := []struct {
		name     string
		result   CfnLintResult
		expected int
	}{
		{
			name:     "empty result",
			result:   CfnLintResult{},
			expected: 0,
		},
		{
			name: "errors only",
			result: CfnLintResult{
				Errors: []string{"error1", "error2"},
			},
			expected: 2,
		},
		{
			name: "warnings only",
			result: CfnLintResult{
				Warnings: []string{"warning1"},
			},
			expected: 1,
		},
		{
			name: "mixed issues",
			result: CfnLintResult{
				Errors:        []string{"error1"},
				Warnings:      []string{"warning1", "warning2"},
				Informational: []string{"info1"},
			},
			expected: 4,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.expected, tt.result.TotalIssues())
		})
	}
}

func TestFormatCfnLintIssue(t *testing.T) {
	tests := []struct {
		name     string
		issue    CfnLintIssue
		expected string
	}{
		{
			name: "simple issue",
			issue: CfnLintIssue{
				Rule:    CfnLintRule{ID: "E1234"},
				Message: "Something is wrong",
			},
			expected: "E1234: Something is wrong",
		},
		{
			name: "issue with path",
			issue: CfnLintIssue{
				Rule:    CfnLintRule{ID: "W5678"},
				Message: "Warning message",
				Location: CfnLintLoc{
					Path: []any{"Resources", "MyBucket", "Properties"},
				},
			},
			expected: "W5678: Warning message (at Resources/MyBucket/Properties)",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := formatCfnLintIssue(tt.issue)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestParseCfnLintRaw(t *testing.T) {
	tests := []struct {
		name         string
		stdout       string
		stderr       string
		expectPassed bool
		expectErrors int
	}{
		{
			name:         "empty output",
			stdout:       "",
			stderr:       "",
			expectPassed: true,
			expectErrors: 0,
		},
		{
			name:         "error in output",
			stdout:       "template.yaml:1:0:E0000:error message",
			stderr:       "",
			expectPassed: false,
			expectErrors: 1,
		},
		{
			name:         "warning in output",
			stdout:       "template.yaml:1:0:W0001:warning message",
			stderr:       "",
			expectPassed: true,
			expectErrors: 0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := parseCfnLintRaw(tt.stdout, tt.stderr)
			require.NoError(t, err)
			assert.Equal(t, tt.expectPassed, result.Passed)
			assert.Equal(t, tt.expectErrors, len(result.Errors))
		})
	}
}

func TestRunCfnLint_FileNotFound(t *testing.T) {
	result, err := RunCfnLint("/nonexistent/template.yaml")
	require.NoError(t, err)
	assert.False(t, result.Passed)
	assert.Len(t, result.Errors, 1)
	assert.Contains(t, result.Errors[0], "Template file not found")
}

func TestRunCfnLint_ValidTemplate(t *testing.T) {
	// Create a valid CloudFormation template
	tempDir := t.TempDir()
	templatePath := filepath.Join(tempDir, "template.yaml")

	validTemplate := `AWSTemplateFormatVersion: '2010-09-09'
Description: Test template
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: test-bucket
`
	err := os.WriteFile(templatePath, []byte(validTemplate), 0644)
	require.NoError(t, err)

	// Skip if cfn-lint is not installed
	if _, err := os.Stat("/usr/local/bin/cfn-lint"); os.IsNotExist(err) {
		// Try to find cfn-lint in PATH
		_, err := os.LookupEnv("PATH")
		if !err {
			t.Skip("cfn-lint not found in PATH")
		}
	}

	result, err := RunCfnLint(templatePath)
	require.NoError(t, err)
	// Result should parse successfully (whether or not there are warnings)
	assert.NotNil(t, result)
}

func TestLintResult_Struct(t *testing.T) {
	result := LintResult{
		Passed: true,
		Issues: []string{},
		Output: "No issues found",
	}

	assert.True(t, result.Passed)
	assert.Empty(t, result.Issues)
}

func TestBuildResult_Struct(t *testing.T) {
	result := BuildResult{
		Success:      true,
		Template:     "AWSTemplateFormatVersion: '2010-09-09'",
		TemplatePath: "/tmp/template.yaml",
	}

	assert.True(t, result.Success)
	assert.NotEmpty(t, result.Template)
	assert.NotEmpty(t, result.TemplatePath)
}

func TestValidationResult_Struct(t *testing.T) {
	result := ValidationResult{
		LintResult: &LintResult{
			Passed: true,
		},
		BuildResult: &BuildResult{
			Success: true,
		},
		CfnLintResult: &CfnLintResult{
			Passed: true,
		},
	}

	assert.True(t, result.LintResult.Passed)
	assert.True(t, result.BuildResult.Success)
	assert.True(t, result.CfnLintResult.Passed)
}

func TestCfnLintIssue_JSON(t *testing.T) {
	// Test that the struct can be parsed from JSON (mimicking cfn-lint output)
	jsonData := `[{
		"Rule": {
			"Id": "E1234",
			"Description": "Test rule",
			"ShortDescription": "Test",
			"Source": "https://example.com"
		},
		"Location": {
			"Start": {"LineNumber": 1, "ColumnNumber": 1},
			"End": {"LineNumber": 1, "ColumnNumber": 10},
			"Path": ["Resources", "MyBucket"],
			"Filename": "template.yaml"
		},
		"Level": "Error",
		"Message": "Test error message"
	}]`

	var issues []CfnLintIssue
	err := json.Unmarshal([]byte(jsonData), &issues)
	require.NoError(t, err)
	require.Len(t, issues, 1)

	issue := issues[0]
	assert.Equal(t, "E1234", issue.Rule.ID)
	assert.Equal(t, "Error", issue.Level)
	assert.Equal(t, "Test error message", issue.Message)
	assert.Equal(t, 1, issue.Location.Start.LineNumber)
}
