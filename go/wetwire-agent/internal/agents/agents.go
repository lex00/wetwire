// Package agents provides AI agents backed by the Anthropic API.
//
// The package provides two main agent types:
// - RunnerAgent: Generates infrastructure code with tool access
// - DeveloperAgent: Simulates a developer using a persona
package agents

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/anthropics/anthropic-sdk-go"
	"github.com/anthropics/anthropic-sdk-go/option"
	"github.com/lex00/wetwire-agent/internal/orchestrator"
	"github.com/lex00/wetwire-agent/internal/results"
)

// RunnerAgent generates infrastructure code using the Anthropic API.
type RunnerAgent struct {
	client         anthropic.Client
	session        *results.Session
	developer      orchestrator.Developer
	workDir        string
	generatedFiles []string
	templateJSON   string
	maxLintCycles  int

	// Lint enforcement state
	lintCalled  bool // Has lint been run at least once?
	lintPassed  bool // Did lint pass on the most recent run?
	pendingLint bool // Does code need linting (written since last lint)?
	lintCycles  int  // Number of lint attempts
}

// RunnerConfig configures the RunnerAgent.
type RunnerConfig struct {
	// APIKey for Anthropic (defaults to ANTHROPIC_API_KEY env var)
	APIKey string

	// Model to use (defaults to claude-sonnet-4-20250514)
	Model string

	// WorkDir is the directory to write generated files
	WorkDir string

	// MaxLintCycles is the maximum number of lint/fix attempts
	MaxLintCycles int

	// Session for tracking results
	Session *results.Session

	// Developer to ask clarifying questions
	Developer orchestrator.Developer
}

// NewRunnerAgent creates a new RunnerAgent.
func NewRunnerAgent(config RunnerConfig) (*RunnerAgent, error) {
	apiKey := config.APIKey
	if apiKey == "" {
		apiKey = os.Getenv("ANTHROPIC_API_KEY")
	}
	if apiKey == "" {
		return nil, fmt.Errorf("ANTHROPIC_API_KEY environment variable not set")
	}

	client := anthropic.NewClient(option.WithAPIKey(apiKey))

	if config.WorkDir == "" {
		config.WorkDir = "."
	}
	if config.MaxLintCycles == 0 {
		config.MaxLintCycles = 3
	}

	return &RunnerAgent{
		client:        client,
		session:       config.Session,
		developer:     config.Developer,
		workDir:       config.WorkDir,
		maxLintCycles: config.MaxLintCycles,
	}, nil
}

// Run executes the runner workflow.
func (r *RunnerAgent) Run(ctx context.Context, prompt string) error {
	systemPrompt := `You are an infrastructure code generator using the wetwire-aws framework.
Your job is to generate Go code that defines AWS CloudFormation resources.

The user will describe what infrastructure they need. You will:
1. Ask clarifying questions if the requirements are unclear
2. Generate Go code using the wetwire-aws patterns
3. Run the linter and fix any issues
4. Build the CloudFormation template

Use the wrapper pattern for all resources:

    var MyBucket = s3.Bucket{
        BucketName: "my-bucket",
    }

    var MyFunction = lambda.Function{
        Role: MyRole.Arn,  // Reference to another resource's attribute
    }

Available tools:
- init_package: Create a new package directory
- write_file: Write a Go file
- read_file: Read a file's contents
- run_lint: Run the linter on the package
- run_build: Build the CloudFormation template
- ask_developer: Ask the developer a clarifying question

Always run_lint after writing files, and fix any issues before running build.`

	tools := r.getTools()

	messages := []anthropic.MessageParam{
		anthropic.NewUserMessage(anthropic.NewTextBlock(prompt)),
	}

	// Agentic loop
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		// Call the API
		resp, err := r.client.Messages.New(ctx, anthropic.MessageNewParams{
			Model:     anthropic.ModelClaudeSonnet4_20250514,
			MaxTokens: 4096,
			System:    []anthropic.TextBlockParam{{Text: systemPrompt}},
			Messages:  messages,
			Tools:     tools,
		})
		if err != nil {
			return fmt.Errorf("API call failed: %w", err)
		}

		// Add assistant response to messages
		messages = append(messages, resp.ToParam())

		// Check for stop reason
		if resp.StopReason == anthropic.StopReasonEndTurn {
			// Completion gate: check if lint requirements are met
			if enforcement := r.checkCompletionGate(resp); enforcement != "" {
				// Force agent to continue
				messages = append(messages, anthropic.NewUserMessage(
					anthropic.NewTextBlock(enforcement),
				))
				continue
			}
			// Agent is done
			break
		}

		// Process tool calls
		if resp.StopReason == anthropic.StopReasonToolUse {
			var toolResults []anthropic.ContentBlockParamUnion
			var toolsCalled []string

			for _, block := range resp.Content {
				if block.Type == "tool_use" {
					result := r.executeTool(ctx, block.Name, block.Input)
					toolResults = append(toolResults, anthropic.NewToolResultBlock(
						block.ID,
						result,
						false,
					))
					toolsCalled = append(toolsCalled, block.Name)
				}
			}

			messages = append(messages, anthropic.NewUserMessage(toolResults...))

			// Check for lint enforcement violations after this turn
			if enforcement := r.checkLintEnforcement(toolsCalled); enforcement != "" {
				messages = append(messages, anthropic.NewUserMessage(
					anthropic.NewTextBlock(enforcement),
				))
			}
		}
	}

	return nil
}

// checkLintEnforcement checks if the agent violated lint enforcement rules.
// Returns an enforcement message if a violation occurred, empty string otherwise.
func (r *RunnerAgent) checkLintEnforcement(toolsCalled []string) string {
	wroteFile := false
	ranLint := false

	for _, tool := range toolsCalled {
		if tool == "write_file" {
			wroteFile = true
		}
		if tool == "run_lint" {
			ranLint = true
		}
	}

	// Enforcement: If write_file was called but run_lint wasn't in the same turn
	if wroteFile && !ranLint {
		return `ENFORCEMENT: You wrote a file but did not call run_lint in the same turn.
You MUST call run_lint immediately after writing code to check for issues.
Call run_lint now before proceeding.`
	}

	return ""
}

// checkCompletionGate checks if the agent can complete.
// Returns an enforcement message if completion is not allowed.
func (r *RunnerAgent) checkCompletionGate(resp *anthropic.Message) string {
	// Extract text from response to check for completion indicators
	var responseText string
	for _, block := range resp.Content {
		if block.Type == "text" {
			responseText += block.Text
		}
	}

	// Check for completion indicators
	lowerText := strings.ToLower(responseText)
	isCompletionAttempt := strings.Contains(lowerText, "done") ||
		strings.Contains(lowerText, "complete") ||
		strings.Contains(lowerText, "finished") ||
		strings.Contains(lowerText, "that's it") ||
		strings.Contains(lowerText, "all set")

	if !isCompletionAttempt && len(r.generatedFiles) == 0 {
		// Agent hasn't written any files yet, let it continue thinking
		return ""
	}

	// Gate 1: Must have called lint at least once
	if !r.lintCalled {
		return `ENFORCEMENT: You cannot complete without running the linter.
You MUST call run_lint to validate your code before finishing.
Call run_lint now.`
	}

	// Gate 2: Code must not be pending lint (written since last lint)
	if r.pendingLint {
		return `ENFORCEMENT: You have written code since the last lint run.
You MUST call run_lint to validate your latest changes before finishing.
Call run_lint now.`
	}

	// Gate 3: Lint must have passed
	if !r.lintPassed {
		return `ENFORCEMENT: The linter found issues that have not been resolved.
You MUST fix the lint errors and run_lint again until it passes.
Review the lint output and fix the issues.`
	}

	// All gates passed
	return ""
}

// AskDeveloper sends a question to the Developer.
func (r *RunnerAgent) AskDeveloper(ctx context.Context, question string) (string, error) {
	if r.developer == nil {
		return "", fmt.Errorf("no developer configured")
	}

	answer, err := r.developer.Respond(ctx, question)
	if err != nil {
		return "", err
	}

	if r.session != nil {
		r.session.AddQuestion(question, answer)
	}

	return answer, nil
}

// GetGeneratedFiles returns the list of generated file paths.
func (r *RunnerAgent) GetGeneratedFiles() []string {
	return r.generatedFiles
}

// GetTemplate returns the generated CloudFormation template JSON.
func (r *RunnerAgent) GetTemplate() string {
	return r.templateJSON
}

// GetLintCycles returns the number of lint attempts.
func (r *RunnerAgent) GetLintCycles() int {
	return r.lintCycles
}

// LintPassed returns whether the last lint run passed.
func (r *RunnerAgent) LintPassed() bool {
	return r.lintPassed
}

// getTools returns the tool definitions for the agent.
func (r *RunnerAgent) getTools() []anthropic.ToolUnionParam {
	return []anthropic.ToolUnionParam{
		{
			OfTool: &anthropic.ToolParam{
				Name:        "init_package",
				Description: anthropic.String("Initialize a new wetwire-aws package directory"),
				InputSchema: anthropic.ToolInputSchemaParam{
					Properties: map[string]any{
						"name": map[string]any{
							"type":        "string",
							"description": "Package name (directory name)",
						},
					},
					Required: []string{"name"},
				},
			},
		},
		{
			OfTool: &anthropic.ToolParam{
				Name:        "write_file",
				Description: anthropic.String("Write content to a Go file"),
				InputSchema: anthropic.ToolInputSchemaParam{
					Properties: map[string]any{
						"path": map[string]any{
							"type":        "string",
							"description": "File path relative to work directory",
						},
						"content": map[string]any{
							"type":        "string",
							"description": "File content",
						},
					},
					Required: []string{"path", "content"},
				},
			},
		},
		{
			OfTool: &anthropic.ToolParam{
				Name:        "read_file",
				Description: anthropic.String("Read a file's contents"),
				InputSchema: anthropic.ToolInputSchemaParam{
					Properties: map[string]any{
						"path": map[string]any{
							"type":        "string",
							"description": "File path relative to work directory",
						},
					},
					Required: []string{"path"},
				},
			},
		},
		{
			OfTool: &anthropic.ToolParam{
				Name:        "run_lint",
				Description: anthropic.String("Run the wetwire-aws linter on the package"),
				InputSchema: anthropic.ToolInputSchemaParam{
					Properties: map[string]any{
						"path": map[string]any{
							"type":        "string",
							"description": "Package path to lint",
						},
					},
					Required: []string{"path"},
				},
			},
		},
		{
			OfTool: &anthropic.ToolParam{
				Name:        "run_build",
				Description: anthropic.String("Build the CloudFormation template from the package"),
				InputSchema: anthropic.ToolInputSchemaParam{
					Properties: map[string]any{
						"path": map[string]any{
							"type":        "string",
							"description": "Package path to build",
						},
					},
					Required: []string{"path"},
				},
			},
		},
		{
			OfTool: &anthropic.ToolParam{
				Name:        "ask_developer",
				Description: anthropic.String("Ask the developer a clarifying question"),
				InputSchema: anthropic.ToolInputSchemaParam{
					Properties: map[string]any{
						"question": map[string]any{
							"type":        "string",
							"description": "The question to ask",
						},
					},
					Required: []string{"question"},
				},
			},
		},
	}
}

// executeTool executes a tool and returns the result.
func (r *RunnerAgent) executeTool(ctx context.Context, name string, input json.RawMessage) string {
	var params map[string]string
	if err := json.Unmarshal(input, &params); err != nil {
		return fmt.Sprintf("Error parsing input: %v", err)
	}

	switch name {
	case "init_package":
		return r.toolInitPackage(params["name"])
	case "write_file":
		return r.toolWriteFile(params["path"], params["content"])
	case "read_file":
		return r.toolReadFile(params["path"])
	case "run_lint":
		return r.toolRunLint(params["path"])
	case "run_build":
		return r.toolRunBuild(params["path"])
	case "ask_developer":
		answer, err := r.AskDeveloper(ctx, params["question"])
		if err != nil {
			return fmt.Sprintf("Error: %v", err)
		}
		return answer
	default:
		return fmt.Sprintf("Unknown tool: %s", name)
	}
}

func (r *RunnerAgent) toolInitPackage(name string) string {
	dir := filepath.Join(r.workDir, name)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Sprintf("Error creating directory: %v", err)
	}
	return fmt.Sprintf("Created package directory: %s", dir)
}

func (r *RunnerAgent) toolWriteFile(path, content string) string {
	fullPath := filepath.Join(r.workDir, path)

	// Ensure parent directory exists
	if err := os.MkdirAll(filepath.Dir(fullPath), 0755); err != nil {
		return fmt.Sprintf("Error creating directory: %v", err)
	}

	if err := os.WriteFile(fullPath, []byte(content), 0644); err != nil {
		return fmt.Sprintf("Error writing file: %v", err)
	}

	r.generatedFiles = append(r.generatedFiles, path)

	// Update lint enforcement state: code needs linting
	r.pendingLint = true
	r.lintPassed = false

	return fmt.Sprintf("Wrote %d bytes to %s", len(content), path)
}

func (r *RunnerAgent) toolReadFile(path string) string {
	fullPath := filepath.Join(r.workDir, path)
	content, err := os.ReadFile(fullPath)
	if err != nil {
		return fmt.Sprintf("Error reading file: %v", err)
	}
	return string(content)
}

func (r *RunnerAgent) toolRunLint(path string) string {
	fullPath := filepath.Join(r.workDir, path)
	cmd := exec.Command("wetwire-aws", "lint", fullPath, "--format", "json")
	output, err := cmd.CombinedOutput()

	result := string(output)

	// Update lint enforcement state
	r.lintCalled = true
	r.pendingLint = false
	r.lintCycles++

	if err != nil {
		// Lint found issues but didn't crash
		r.lintPassed = false
		if exitErr, ok := err.(*exec.ExitError); ok && exitErr.ExitCode() == 2 {
			// Parse issues for session tracking
			var lintResult struct {
				Success bool `json:"success"`
				Issues  []struct {
					Message string `json:"message"`
				} `json:"issues"`
			}
			if json.Unmarshal(output, &lintResult) == nil && r.session != nil {
				issues := make([]string, len(lintResult.Issues))
				for i, issue := range lintResult.Issues {
					issues[i] = issue.Message
				}
				r.session.AddLintCycle(issues, r.lintCycles, false)
			}
		}
	} else {
		// Lint passed
		r.lintPassed = true
		if r.session != nil {
			r.session.AddLintCycle(nil, r.lintCycles, true)
		}
	}

	return result
}

func (r *RunnerAgent) toolRunBuild(path string) string {
	fullPath := filepath.Join(r.workDir, path)
	cmd := exec.Command("wetwire-aws", "build", fullPath, "--format", "json")
	output, err := cmd.CombinedOutput()

	result := string(output)
	if err == nil {
		// Extract template JSON
		var buildResult struct {
			Success  bool   `json:"success"`
			Template interface{} `json:"template"`
		}
		if json.Unmarshal(output, &buildResult) == nil && buildResult.Success {
			if templateData, err := json.Marshal(buildResult.Template); err == nil {
				r.templateJSON = string(templateData)
			}
		}
	}

	return result
}

// CreateDeveloperResponder creates a responder function for AIDeveloper.
func CreateDeveloperResponder(apiKey string) func(ctx context.Context, systemPrompt, message string) (string, error) {
	if apiKey == "" {
		apiKey = os.Getenv("ANTHROPIC_API_KEY")
	}

	client := anthropic.NewClient(option.WithAPIKey(apiKey))

	return func(ctx context.Context, systemPrompt, message string) (string, error) {
		resp, err := client.Messages.New(ctx, anthropic.MessageNewParams{
			Model:     anthropic.ModelClaude3_5HaikuLatest,
			MaxTokens: 1024,
			System:    []anthropic.TextBlockParam{{Text: systemPrompt}},
			Messages: []anthropic.MessageParam{
				anthropic.NewUserMessage(anthropic.NewTextBlock(message)),
			},
		})
		if err != nil {
			return "", err
		}

		var response strings.Builder
		for _, block := range resp.Content {
			if block.Type == "text" {
				response.WriteString(block.Text)
			}
		}

		return response.String(), nil
	}
}
