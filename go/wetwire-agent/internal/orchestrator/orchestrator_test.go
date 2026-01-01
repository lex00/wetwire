package orchestrator

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/lex00/wetwire-agent/internal/personas"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// MockRunner is a test implementation of the Runner interface.
type MockRunner struct {
	RunFunc           func(ctx context.Context, prompt string) error
	AskDeveloperFunc  func(ctx context.Context, question string) (string, error)
	GeneratedFiles    []string
	TemplateJSON      string
	QuestionsAsked    []string
	PromptReceived    string
}

func (m *MockRunner) Run(ctx context.Context, prompt string) error {
	m.PromptReceived = prompt
	if m.RunFunc != nil {
		return m.RunFunc(ctx, prompt)
	}
	return nil
}

func (m *MockRunner) AskDeveloper(ctx context.Context, question string) (string, error) {
	m.QuestionsAsked = append(m.QuestionsAsked, question)
	if m.AskDeveloperFunc != nil {
		return m.AskDeveloperFunc(ctx, question)
	}
	return "yes", nil
}

func (m *MockRunner) GetGeneratedFiles() []string {
	return m.GeneratedFiles
}

func (m *MockRunner) GetTemplate() string {
	return m.TemplateJSON
}

// MockDeveloper is a test implementation of the Developer interface.
type MockDeveloper struct {
	RespondFunc   func(ctx context.Context, message string) (string, error)
	Responses     []string
	responseIndex int
}

func (m *MockDeveloper) Respond(ctx context.Context, message string) (string, error) {
	if m.RespondFunc != nil {
		return m.RespondFunc(ctx, message)
	}
	if m.responseIndex < len(m.Responses) {
		resp := m.Responses[m.responseIndex]
		m.responseIndex++
		return resp, nil
	}
	return "", nil
}

func TestDefaultConfig(t *testing.T) {
	config := DefaultConfig()

	assert.Equal(t, 3, config.MaxLintCycles)
	assert.Equal(t, 10*time.Minute, config.Timeout)
}

func TestNew(t *testing.T) {
	config := Config{
		Persona:       personas.Beginner,
		Scenario:      "test",
		InitialPrompt: "I need a bucket",
		MaxLintCycles: 3,
		OutputDir:     "./output",
		Timeout:       5 * time.Minute,
	}

	developer := &MockDeveloper{}
	runner := &MockRunner{}

	orch := New(config, developer, runner)

	assert.NotNil(t, orch)
	assert.Equal(t, config, orch.config)
	assert.NotNil(t, orch.session)
	assert.Equal(t, "beginner", orch.session.Persona)
	assert.Equal(t, "test", orch.session.Scenario)
}

func TestOrchestrator_Run_Success(t *testing.T) {
	config := Config{
		Persona:       personas.Beginner,
		Scenario:      "test",
		InitialPrompt: "Create a bucket for logs",
	}

	developer := &MockDeveloper{}
	runner := &MockRunner{
		GeneratedFiles: []string{"storage.go"},
		TemplateJSON:   `{"AWSTemplateFormatVersion": "2010-09-09"}`,
	}

	orch := New(config, developer, runner)

	ctx := context.Background()
	session, err := orch.Run(ctx)

	require.NoError(t, err)
	assert.NotNil(t, session)
	assert.Equal(t, "Create a bucket for logs", session.InitialPrompt)
	assert.Equal(t, []string{"storage.go"}, session.GeneratedFiles)
	assert.NotEmpty(t, session.TemplateJSON)
	assert.False(t, session.EndTime.IsZero())

	// Verify first message is from developer
	assert.Len(t, session.Messages, 1)
	assert.Equal(t, "developer", session.Messages[0].Role)
	assert.Equal(t, "Create a bucket for logs", session.Messages[0].Content)

	// Verify runner received the prompt
	assert.Equal(t, "Create a bucket for logs", runner.PromptReceived)
}

func TestOrchestrator_Run_RunnerError(t *testing.T) {
	config := Config{
		Persona:       personas.Beginner,
		Scenario:      "test",
		InitialPrompt: "Create a bucket",
	}

	developer := &MockDeveloper{}
	runner := &MockRunner{
		RunFunc: func(ctx context.Context, prompt string) error {
			return errors.New("API rate limit exceeded")
		},
	}

	orch := New(config, developer, runner)

	ctx := context.Background()
	session, err := orch.Run(ctx)

	require.Error(t, err)
	assert.Contains(t, err.Error(), "runner failed")
	assert.Contains(t, err.Error(), "API rate limit exceeded")
	assert.NotNil(t, session)
}

func TestOrchestrator_Run_WithTimeout(t *testing.T) {
	config := Config{
		Persona:       personas.Beginner,
		Scenario:      "test",
		InitialPrompt: "Create a bucket",
		Timeout:       100 * time.Millisecond,
	}

	developer := &MockDeveloper{}
	runner := &MockRunner{
		RunFunc: func(ctx context.Context, prompt string) error {
			// Simulate slow operation
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(500 * time.Millisecond):
				return nil
			}
		},
	}

	orch := New(config, developer, runner)

	ctx := context.Background()
	_, err := orch.Run(ctx)

	require.Error(t, err)
	assert.Contains(t, err.Error(), "context deadline exceeded")
}

func TestOrchestrator_CalculateScore(t *testing.T) {
	config := Config{
		Persona:  personas.Beginner,
		Scenario: "test",
	}

	developer := &MockDeveloper{}
	runner := &MockRunner{}

	orch := New(config, developer, runner)

	// Add some lint cycles
	orch.session.AddLintCycle([]string{"error1"}, 1, false)
	orch.session.AddLintCycle([]string{}, 0, true)

	// Add some questions
	orch.session.AddQuestion("Encryption?", "SSE-S3")

	score := orch.CalculateScore(
		3,    // expected resources
		3,    // actual resources
		true, // lint passed
		nil,  // no code issues
		0,    // no cfn errors
		0,    // no cfn warnings
	)

	assert.NotNil(t, score)
	assert.Equal(t, "beginner", score.Persona)
	assert.Equal(t, "test", score.Scenario)

	// Check dimensions are populated
	assert.Equal(t, 3, score.Completeness.Rating) // All resources
	assert.Equal(t, 2, score.LintQuality.Rating)  // Passed after cycles
	assert.Equal(t, 3, score.CodeQuality.Rating)  // No issues
	assert.Equal(t, 3, score.OutputValidity.Rating)
	assert.Equal(t, 3, score.QuestionEfficiency.Rating) // 1 question is optimal

	// Verify score is attached to session
	assert.Equal(t, score, orch.session.Score)
}

func TestOrchestrator_CalculateScore_Partial(t *testing.T) {
	config := Config{
		Persona:  personas.Expert,
		Scenario: "complex",
	}

	orch := New(config, &MockDeveloper{}, &MockRunner{})

	// Simulate some failures
	orch.session.AddLintCycle([]string{"error1", "error2"}, 0, false)
	orch.session.AddLintCycle([]string{"error1", "error2"}, 0, false)
	orch.session.AddLintCycle([]string{"error1", "error2"}, 0, false)

	score := orch.CalculateScore(
		5,     // expected resources
		3,     // actual resources (missing some)
		false, // lint failed
		[]string{"missing import", "unused variable"},
		1, // cfn errors
		2, // cfn warnings
	)

	assert.Less(t, score.Completeness.Rating, 3)
	assert.Less(t, score.LintQuality.Rating, 3)
	assert.Less(t, score.CodeQuality.Rating, 3)
	assert.Less(t, score.OutputValidity.Rating, 3)
}

func TestOrchestrator_Session(t *testing.T) {
	config := Config{
		Persona:  personas.Beginner,
		Scenario: "test",
	}

	orch := New(config, &MockDeveloper{}, &MockRunner{})

	session := orch.Session()

	assert.NotNil(t, session)
	assert.Equal(t, "beginner", session.Persona)
}

func TestHumanDeveloper(t *testing.T) {
	responses := []string{"Yes", "SSE-S3", "90 days"}
	index := 0

	reader := func() (string, error) {
		if index < len(responses) {
			resp := responses[index]
			index++
			return resp, nil
		}
		return "", errors.New("no more responses")
	}

	dev := NewHumanDeveloper(reader)

	ctx := context.Background()

	resp1, err := dev.Respond(ctx, "Enable versioning?")
	require.NoError(t, err)
	assert.Equal(t, "Yes", resp1)

	resp2, err := dev.Respond(ctx, "Encryption type?")
	require.NoError(t, err)
	assert.Equal(t, "SSE-S3", resp2)
}

func TestAIDeveloper(t *testing.T) {
	persona := personas.Beginner

	var receivedSystem, receivedMessage string
	responder := func(ctx context.Context, systemPrompt, message string) (string, error) {
		receivedSystem = systemPrompt
		receivedMessage = message
		return "Yes, please add that", nil
	}

	dev := NewAIDeveloper(persona, responder)

	ctx := context.Background()
	resp, err := dev.Respond(ctx, "Should I add encryption?")

	require.NoError(t, err)
	assert.Equal(t, "Yes, please add that", resp)
	assert.Equal(t, persona.SystemPrompt, receivedSystem)
	assert.Equal(t, "Should I add encryption?", receivedMessage)
}
