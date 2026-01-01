package results

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/lex00/wetwire-agent/internal/scoring"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestNewSession(t *testing.T) {
	session := NewSession("beginner", "s3_bucket")

	assert.Equal(t, "beginner", session.Persona)
	assert.Equal(t, "s3_bucket", session.Scenario)
	assert.NotEmpty(t, session.ID)
	assert.NotZero(t, session.StartTime)
	assert.Empty(t, session.Messages)
	assert.Empty(t, session.Questions)
	assert.Empty(t, session.LintCycles)
}

func TestSession_AddMessage(t *testing.T) {
	session := NewSession("test", "test")

	session.AddMessage("developer", "I need a bucket")
	session.AddMessage("runner", "What encryption do you want?")
	session.AddMessage("developer", "SSE-S3")

	assert.Len(t, session.Messages, 3)

	assert.Equal(t, "developer", session.Messages[0].Role)
	assert.Equal(t, "I need a bucket", session.Messages[0].Content)

	assert.Equal(t, "runner", session.Messages[1].Role)
	assert.Equal(t, "What encryption do you want?", session.Messages[1].Content)
}

func TestSession_AddQuestion(t *testing.T) {
	session := NewSession("test", "test")

	session.AddQuestion("What encryption?", "SSE-S3")
	session.AddQuestion("Versioning?", "Yes")

	assert.Len(t, session.Questions, 2)

	assert.Equal(t, "What encryption?", session.Questions[0].Question)
	assert.Equal(t, "SSE-S3", session.Questions[0].Answer)
}

func TestSession_AddLintCycle(t *testing.T) {
	session := NewSession("test", "test")

	session.AddLintCycle([]string{"error1", "error2"}, 1, false)
	session.AddLintCycle([]string{"error1"}, 1, true)

	assert.Len(t, session.LintCycles, 2)

	assert.Equal(t, 1, session.LintCycles[0].Cycle)
	assert.Equal(t, 2, session.LintCycles[0].IssueCount)
	assert.Equal(t, 1, session.LintCycles[0].FixedCount)
	assert.False(t, session.LintCycles[0].Passed)

	assert.Equal(t, 2, session.LintCycles[1].Cycle)
	assert.True(t, session.LintCycles[1].Passed)
}

func TestSession_Complete(t *testing.T) {
	session := NewSession("test", "test")

	assert.True(t, session.EndTime.IsZero())

	session.Complete()

	assert.False(t, session.EndTime.IsZero())
	assert.True(t, session.EndTime.After(session.StartTime) || session.EndTime.Equal(session.StartTime))
}

func TestSession_Duration(t *testing.T) {
	session := NewSession("test", "test")

	// Before completion, duration is since start
	time.Sleep(1 * time.Millisecond) // Ensure some time has passed
	duration := session.Duration()
	assert.Greater(t, duration.Nanoseconds(), int64(0))

	// After completion, duration is fixed
	time.Sleep(10 * time.Millisecond)
	session.Complete()

	fixedDuration := session.Duration()
	time.Sleep(10 * time.Millisecond)
	assert.Equal(t, fixedDuration, session.Duration())
}

func TestSession_JSON(t *testing.T) {
	session := NewSession("beginner", "s3_bucket")
	session.InitialPrompt = "I need a bucket"
	session.AddMessage("developer", "I need a bucket")
	session.AddQuestion("Encryption?", "SSE-S3")
	session.AddLintCycle([]string{}, 0, true)
	session.GeneratedFiles = []string{"storage.go"}
	session.Complete()

	data, err := json.Marshal(session)
	require.NoError(t, err)

	var parsed map[string]any
	require.NoError(t, json.Unmarshal(data, &parsed))

	assert.Equal(t, "beginner", parsed["persona"])
	assert.Equal(t, "s3_bucket", parsed["scenario"])
	assert.Equal(t, "I need a bucket", parsed["initial_prompt"])

	messages := parsed["messages"].([]any)
	assert.Len(t, messages, 1)

	questions := parsed["questions"].([]any)
	assert.Len(t, questions, 1)

	files := parsed["generated_files"].([]any)
	assert.Contains(t, files, "storage.go")
}

func TestWriter_Write(t *testing.T) {
	// Create temp directory
	tmpDir, err := os.MkdirTemp("", "results-test-*")
	require.NoError(t, err)
	defer os.RemoveAll(tmpDir)

	// Create session with score
	session := NewSession("beginner", "test")
	session.InitialPrompt = "Test prompt"
	session.AddMessage("developer", "Test message")
	session.GeneratedFiles = []string{"test.go"}
	session.Complete()

	score := scoring.NewScore("beginner", "test")
	score.Completeness.Rating = 3
	score.Completeness.Notes = "All resources generated"
	session.Score = score

	// Write results
	writer := NewWriter(tmpDir)
	err = writer.Write(session)
	require.NoError(t, err)

	// Verify RESULTS.md was created
	resultsPath := filepath.Join(tmpDir, "beginner", "RESULTS.md")
	assert.FileExists(t, resultsPath)

	content, err := os.ReadFile(resultsPath)
	require.NoError(t, err)
	assert.Contains(t, string(content), "Session Results")
	assert.Contains(t, string(content), "beginner")
	assert.Contains(t, string(content), "Test prompt")

	// Verify session.json was created
	sessionPath := filepath.Join(tmpDir, "beginner", "session.json")
	assert.FileExists(t, sessionPath)

	sessionData, err := os.ReadFile(sessionPath)
	require.NoError(t, err)

	var parsedSession Session
	require.NoError(t, json.Unmarshal(sessionData, &parsedSession))
	assert.Equal(t, "beginner", parsedSession.Persona)

	// Verify score.json was created
	scorePath := filepath.Join(tmpDir, "beginner", "score.json")
	assert.FileExists(t, scorePath)
}

func TestWriter_FormatMarkdown(t *testing.T) {
	session := NewSession("expert", "lambda_api")
	session.InitialPrompt = "Lambda with API Gateway"
	session.AddMessage("developer", "Lambda with API Gateway")
	session.AddMessage("runner", "I'll create the Lambda function")
	session.AddQuestion("Runtime?", "Python 3.12")
	session.AddLintCycle([]string{"error1"}, 1, false)
	session.AddLintCycle([]string{}, 0, true)
	session.GeneratedFiles = []string{"compute.go", "api.go"}
	session.Suggestions = []string{"Add better error handling"}
	session.Complete()

	score := scoring.NewScore("expert", "lambda_api")
	score.Completeness.Rating = 3
	score.LintQuality.Rating = 2
	score.CodeQuality.Rating = 3
	score.OutputValidity.Rating = 3
	score.QuestionEfficiency.Rating = 2
	session.Score = score

	writer := NewWriter("")
	md := writer.formatMarkdown(session)

	// Check header
	assert.Contains(t, md, "# Session Results")
	assert.Contains(t, md, "**Persona:** expert")
	assert.Contains(t, md, "**Scenario:** lambda_api")

	// Check score section
	assert.Contains(t, md, "## Score")
	assert.Contains(t, md, "Completeness")

	// Check prompt section
	assert.Contains(t, md, "## Initial Prompt")
	assert.Contains(t, md, "Lambda with API Gateway")

	// Check questions section
	assert.Contains(t, md, "## Clarifying Questions")
	assert.Contains(t, md, "Runtime?")
	assert.Contains(t, md, "Python 3.12")

	// Check lint cycles
	assert.Contains(t, md, "## Lint Cycles")
	assert.Contains(t, md, "Cycle 1")
	assert.Contains(t, md, "Cycle 2")
	assert.Contains(t, md, "Passed")

	// Check generated files
	assert.Contains(t, md, "## Generated Files")
	assert.Contains(t, md, "compute.go")
	assert.Contains(t, md, "api.go")

	// Check conversation log
	assert.Contains(t, md, "## Conversation Log")

	// Check suggestions
	assert.Contains(t, md, "## Improvement Suggestions")
	assert.Contains(t, md, "Add better error handling")
}

func TestMessage_ToolCalls(t *testing.T) {
	msg := Message{
		Role:      "runner",
		Content:   "Creating file",
		Timestamp: time.Now(),
		ToolCalls: []ToolCall{
			{
				Name:   "write_file",
				Input:  "storage.go",
				Output: "File created",
			},
			{
				Name:   "run_lint",
				Input:  "./",
				Output: "No issues",
			},
		},
	}

	data, err := json.Marshal(msg)
	require.NoError(t, err)

	var parsed map[string]any
	require.NoError(t, json.Unmarshal(data, &parsed))

	toolCalls := parsed["tool_calls"].([]any)
	assert.Len(t, toolCalls, 2)

	call1 := toolCalls[0].(map[string]any)
	assert.Equal(t, "write_file", call1["name"])
	assert.Equal(t, "storage.go", call1["input"])
}

func TestGenerateID(t *testing.T) {
	id1 := generateID()
	time.Sleep(2 * time.Second) // Ensure different timestamp
	id2 := generateID()

	// IDs should be unique
	assert.NotEqual(t, id1, id2)

	// IDs should have expected prefix
	assert.Contains(t, id1, "session_")
	assert.Contains(t, id2, "session_")
}
