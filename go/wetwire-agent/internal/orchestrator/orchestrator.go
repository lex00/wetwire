// Package orchestrator coordinates the Developer and Runner agents.
//
// The orchestrator manages the two-agent workflow:
// 1. Developer provides requirements (human or AI persona)
// 2. Runner generates code and asks clarifying questions
// 3. Runner runs lint cycles and fixes issues
// 4. Orchestrator tracks results and calculates score
package orchestrator

import (
	"context"
	"fmt"
	"time"

	"github.com/lex00/wetwire-agent/internal/personas"
	"github.com/lex00/wetwire-agent/internal/results"
	"github.com/lex00/wetwire-agent/internal/scoring"
)

// Developer is the interface for the Developer role (human or AI).
type Developer interface {
	// Respond generates a response to the Runner's message.
	Respond(ctx context.Context, message string) (string, error)
}

// Runner is the interface for the Runner agent.
type Runner interface {
	// Run executes the runner workflow with the given prompt.
	Run(ctx context.Context, prompt string) error

	// AskDeveloper sends a question to the Developer.
	AskDeveloper(ctx context.Context, question string) (string, error)

	// GetGeneratedFiles returns the list of generated file paths.
	GetGeneratedFiles() []string

	// GetTemplate returns the generated CloudFormation template JSON.
	GetTemplate() string
}

// Config configures an orchestration session.
type Config struct {
	// Persona for the Developer (used in testing mode)
	Persona personas.Persona

	// Scenario name for tracking
	Scenario string

	// InitialPrompt from the Developer
	InitialPrompt string

	// MaxLintCycles is the maximum number of lint/fix cycles
	MaxLintCycles int

	// OutputDir for results
	OutputDir string

	// Timeout for the entire session
	Timeout time.Duration
}

// DefaultConfig returns a Config with sensible defaults.
func DefaultConfig() Config {
	return Config{
		MaxLintCycles: 3,
		Timeout:       10 * time.Minute,
	}
}

// Orchestrator coordinates Developer and Runner agents.
type Orchestrator struct {
	config    Config
	developer Developer
	runner    Runner
	session   *results.Session
}

// New creates a new Orchestrator.
func New(config Config, developer Developer, runner Runner) *Orchestrator {
	return &Orchestrator{
		config:    config,
		developer: developer,
		runner:    runner,
		session:   results.NewSession(config.Persona.Name, config.Scenario),
	}
}

// Run executes the orchestration workflow.
func (o *Orchestrator) Run(ctx context.Context) (*results.Session, error) {
	// Apply timeout
	if o.config.Timeout > 0 {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(ctx, o.config.Timeout)
		defer cancel()
	}

	o.session.InitialPrompt = o.config.InitialPrompt
	o.session.AddMessage("developer", o.config.InitialPrompt)

	// Run the Runner agent
	if err := o.runner.Run(ctx, o.config.InitialPrompt); err != nil {
		return o.session, fmt.Errorf("runner failed: %w", err)
	}

	// Collect results
	o.session.GeneratedFiles = o.runner.GetGeneratedFiles()
	o.session.TemplateJSON = o.runner.GetTemplate()

	// Complete the session
	o.session.Complete()

	return o.session, nil
}

// CalculateScore calculates the final score for the session.
func (o *Orchestrator) CalculateScore(
	expectedResources int,
	actualResources int,
	lintPassed bool,
	codeIssues []string,
	cfnErrors int,
	cfnWarnings int,
) *scoring.Score {
	score := scoring.NewScore(o.config.Persona.Name, o.config.Scenario)

	// Completeness
	rating, notes := scoring.ScoreCompleteness(expectedResources, actualResources)
	score.Completeness.Rating = rating
	score.Completeness.Notes = notes

	// Lint quality
	lintCycles := len(o.session.LintCycles)
	rating, notes = scoring.ScoreLintQuality(lintCycles, lintPassed)
	score.LintQuality.Rating = rating
	score.LintQuality.Notes = notes
	score.LintCycles = lintCycles

	// Code quality
	rating, notes = scoring.ScoreCodeQuality(codeIssues)
	score.CodeQuality.Rating = rating
	score.CodeQuality.Notes = notes

	// Output validity
	rating, notes = scoring.ScoreOutputValidity(cfnErrors, cfnWarnings)
	score.OutputValidity.Rating = rating
	score.OutputValidity.Notes = notes

	// Question efficiency
	questionCount := len(o.session.Questions)
	rating, notes = scoring.ScoreQuestionEfficiency(questionCount)
	score.QuestionEfficiency.Rating = rating
	score.QuestionEfficiency.Notes = notes
	score.QuestionCount = questionCount

	o.session.Score = score
	return score
}

// Session returns the current session.
func (o *Orchestrator) Session() *results.Session {
	return o.session
}

// HumanDeveloper is a Developer that reads from stdin.
type HumanDeveloper struct {
	reader func() (string, error)
}

// NewHumanDeveloper creates a Developer that prompts the user for input.
func NewHumanDeveloper(reader func() (string, error)) *HumanDeveloper {
	return &HumanDeveloper{reader: reader}
}

// Respond prompts the user and returns their input.
func (h *HumanDeveloper) Respond(ctx context.Context, message string) (string, error) {
	fmt.Printf("\n[Runner asks]: %s\n\n", message)
	fmt.Print("[Your answer]: ")
	return h.reader()
}

// AIDeveloper is a Developer backed by an AI agent with a persona.
type AIDeveloper struct {
	persona  personas.Persona
	responder func(ctx context.Context, systemPrompt, message string) (string, error)
}

// NewAIDeveloper creates a Developer backed by an AI with the given persona.
func NewAIDeveloper(persona personas.Persona, responder func(ctx context.Context, systemPrompt, message string) (string, error)) *AIDeveloper {
	return &AIDeveloper{
		persona:   persona,
		responder: responder,
	}
}

// Respond uses the AI to generate a response in character.
func (a *AIDeveloper) Respond(ctx context.Context, message string) (string, error) {
	return a.responder(ctx, a.persona.SystemPrompt, message)
}
