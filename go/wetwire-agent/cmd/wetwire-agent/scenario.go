package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/lex00/wetwire-agent/internal/agents"
	"github.com/lex00/wetwire-agent/internal/orchestrator"
	"github.com/lex00/wetwire-agent/internal/personas"
	"github.com/lex00/wetwire-agent/internal/results"
	"github.com/lex00/wetwire-agent/internal/scoring"
	"github.com/lex00/wetwire-agent/internal/validation"
	"github.com/spf13/cobra"
)

// scenarioFlags holds all flags for the run-scenario command.
type scenarioFlags struct {
	personaName  string
	generate     bool
	saveResults  bool
	saveExpected bool
	ciMode       bool
	failFast     bool
}

func newRunScenarioCmd() *cobra.Command {
	flags := &scenarioFlags{}

	cmd := &cobra.Command{
		Use:   "run-scenario <scenario-path>",
		Short: "Run a predefined scenario",
		Long: `Run a scenario from the scenarios directory.

Scenarios are organized as:
    scenarios/
    ├── s3_log_bucket/
    │   ├── prompts/
    │   │   ├── beginner.md
    │   │   └── expert.md
    │   ├── expected/
    │   │   └── storage.go
    │   └── results/
    │       └── beginner/

Examples:
    wetwire-agent run-scenario ./scenarios/s3_log_bucket
    wetwire-agent run-scenario ./scenarios/s3_log_bucket --persona beginner --generate
    wetwire-agent run-scenario ./scenarios/s3_log_bucket --persona all --save-results
    wetwire-agent run-scenario ./scenarios/s3_log_bucket --generate --save-expected
    wetwire-agent run-scenario ./scenarios/s3_log_bucket --ci`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return runScenario(args[0], flags)
		},
	}

	cmd.Flags().StringVarP(&flags.personaName, "persona", "p", "", "Persona to use (or 'all')")
	cmd.Flags().BoolVar(&flags.generate, "generate", false, "Generate code using AI (otherwise just validate expected/)")
	cmd.Flags().BoolVar(&flags.saveResults, "save-results", false, "Save results to scenario results/ directory")
	cmd.Flags().BoolVar(&flags.saveExpected, "save-expected", false, "Save generated code as new expected output (requires --generate)")
	cmd.Flags().BoolVar(&flags.ciMode, "ci", false, "CI mode: exit with failure if score < 10")
	cmd.Flags().BoolVar(&flags.failFast, "fail-fast", false, "Stop on first failure (with --persona all)")

	return cmd
}

// Scenario represents a test scenario configuration.
type Scenario struct {
	Name           string
	Path           string
	ExpectedDir    string
	PromptsDir     string
	ResultsDir     string
	ExpectedFiles  []string
	AvailablePersonas []string
}

func loadScenario(scenarioPath string) (*Scenario, error) {
	info, err := os.Stat(scenarioPath)
	if err != nil {
		return nil, fmt.Errorf("scenario not found: %w", err)
	}
	if !info.IsDir() {
		return nil, fmt.Errorf("scenario path must be a directory")
	}

	scenario := &Scenario{
		Name:        filepath.Base(scenarioPath),
		Path:        scenarioPath,
		ExpectedDir: filepath.Join(scenarioPath, "expected"),
		PromptsDir:  filepath.Join(scenarioPath, "prompts"),
		ResultsDir:  filepath.Join(scenarioPath, "results"),
	}

	// Find expected files
	if entries, err := os.ReadDir(scenario.ExpectedDir); err == nil {
		for _, e := range entries {
			if !e.IsDir() && filepath.Ext(e.Name()) == ".go" {
				scenario.ExpectedFiles = append(scenario.ExpectedFiles, e.Name())
			}
		}
	}

	// Find available personas (from prompts directory)
	if entries, err := os.ReadDir(scenario.PromptsDir); err == nil {
		for _, e := range entries {
			if !e.IsDir() && filepath.Ext(e.Name()) == ".md" {
				name := e.Name()[:len(e.Name())-3] // Remove .md
				scenario.AvailablePersonas = append(scenario.AvailablePersonas, name)
			}
		}
	}

	return scenario, nil
}

func runScenario(scenarioPath string, flags *scenarioFlags) error {
	scenario, err := loadScenario(scenarioPath)
	if err != nil {
		return err
	}

	// Validate flag combinations
	if flags.saveExpected && !flags.generate {
		return fmt.Errorf("--save-expected requires --generate")
	}

	fmt.Printf("Scenario: %s\n", scenario.Name)
	fmt.Printf("Expected files: %v\n", scenario.ExpectedFiles)
	fmt.Printf("Available personas: %v\n\n", scenario.AvailablePersonas)

	if !flags.generate {
		// Just validate the expected directory
		err := validateExpected(scenario)
		if err != nil && flags.ciMode {
			os.Exit(1)
		}
		return err
	}

	// Run with AI generation
	if flags.personaName == "" {
		return fmt.Errorf("--persona required when using --generate")
	}

	if flags.personaName == "all" {
		var anyFailed bool
		for _, p := range scenario.AvailablePersonas {
			fmt.Printf("\n=== Running persona: %s ===\n", p)
			passed, err := runScenarioWithPersona(scenario, p, flags)
			if err != nil {
				fmt.Printf("Error: %v\n", err)
				anyFailed = true
				if flags.failFast {
					break
				}
			} else if !passed {
				anyFailed = true
				if flags.failFast {
					break
				}
			}
		}
		if anyFailed && flags.ciMode {
			return fmt.Errorf("one or more personas failed")
		}
		return nil
	}

	passed, err := runScenarioWithPersona(scenario, flags.personaName, flags)
	if err != nil {
		return err
	}
	if !passed && flags.ciMode {
		return fmt.Errorf("scenario failed with score < 10")
	}
	return nil
}

func validateExpected(scenario *Scenario) error {
	fmt.Println("Validating expected/ directory...")
	fmt.Println()

	// Create temp directory for build output
	tempDir, err := os.MkdirTemp("", "wetwire-validate-*")
	if err != nil {
		return fmt.Errorf("creating temp directory: %w", err)
	}
	defer os.RemoveAll(tempDir)

	// Run full validation pipeline
	result, err := validation.ValidatePackage(scenario.ExpectedDir, tempDir)
	if err != nil {
		return fmt.Errorf("validation failed: %w", err)
	}

	// Print lint results
	fmt.Println("=== wetwire-aws lint ===")
	if result.LintResult.Passed {
		fmt.Println("Status: PASS")
	} else {
		fmt.Println("Status: FAIL")
		fmt.Printf("Issues: %d\n", len(result.LintResult.Issues))
		for _, issue := range result.LintResult.Issues {
			fmt.Printf("  - %s\n", issue)
		}
	}
	fmt.Println()

	// Print build results
	fmt.Println("=== wetwire-aws build ===")
	if result.BuildResult.Success {
		fmt.Println("Status: SUCCESS")
		if result.BuildResult.TemplatePath != "" {
			fmt.Printf("Template: %s\n", result.BuildResult.TemplatePath)
		}
	} else {
		fmt.Println("Status: FAILED")
		if result.BuildResult.Error != "" {
			fmt.Printf("Error: %s\n", result.BuildResult.Error)
		}
	}
	fmt.Println()

	// Print cfn-lint results
	fmt.Println("=== cfn-lint ===")
	if result.CfnLintResult.Passed {
		fmt.Println("Status: PASS")
	} else {
		fmt.Println("Status: FAIL")
	}
	fmt.Printf("Errors: %d\n", len(result.CfnLintResult.Errors))
	fmt.Printf("Warnings: %d\n", len(result.CfnLintResult.Warnings))
	fmt.Printf("Informational: %d\n", len(result.CfnLintResult.Informational))

	if len(result.CfnLintResult.Errors) > 0 {
		fmt.Println("\nErrors:")
		for _, e := range result.CfnLintResult.Errors {
			fmt.Printf("  - %s\n", e)
		}
	}
	if len(result.CfnLintResult.Warnings) > 0 {
		fmt.Println("\nWarnings:")
		for _, w := range result.CfnLintResult.Warnings {
			fmt.Printf("  - %s\n", w)
		}
	}
	fmt.Println()

	// Calculate and display score
	score := calculateValidationScore(scenario, result)
	fmt.Println("=== Score ===")
	fmt.Printf("Total: %d/15 (%s)\n", score.Total(), score.Threshold())
	fmt.Printf("Passed: %v\n", score.Passed())
	fmt.Println()
	fmt.Printf("  Completeness:        %d/3 - %s\n", score.Completeness.Rating, score.Completeness.Notes)
	fmt.Printf("  Lint Quality:        %d/3 - %s\n", score.LintQuality.Rating, score.LintQuality.Notes)
	fmt.Printf("  Code Quality:        %d/3 - %s\n", score.CodeQuality.Rating, score.CodeQuality.Notes)
	fmt.Printf("  Output Validity:     %d/3 - %s\n", score.OutputValidity.Rating, score.OutputValidity.Notes)
	fmt.Printf("  Question Efficiency: %d/3 - %s\n", score.QuestionEfficiency.Rating, score.QuestionEfficiency.Notes)

	// Return error if validation failed
	if !score.Passed() {
		return fmt.Errorf("validation failed with score %d/15", score.Total())
	}

	return nil
}

// calculateValidationScore calculates a score from validation results.
func calculateValidationScore(scenario *Scenario, result *validation.ValidationResult) *scoring.Score {
	score := scoring.NewScore("validation", scenario.Name)

	// Completeness: Check if expected files exist and build succeeded
	if result.BuildResult.Success && result.BuildResult.Template != "" {
		rating, notes := scoring.ScoreCompleteness(len(scenario.ExpectedFiles), len(scenario.ExpectedFiles))
		score.Completeness.Rating = rating
		score.Completeness.Notes = notes
	} else {
		score.Completeness.Rating = scoring.RatingNone
		score.Completeness.Notes = "Build failed"
	}

	// Lint quality: Based on lint result
	if result.LintResult.Passed {
		score.LintQuality.Rating = scoring.RatingExcellent
		score.LintQuality.Notes = "Passed on first check"
	} else {
		score.LintQuality.Rating = scoring.RatingNone
		score.LintQuality.Notes = fmt.Sprintf("%d lint issues", len(result.LintResult.Issues))
	}

	// Code quality: Combine lint and cfn-lint issues
	totalIssues := len(result.LintResult.Issues)
	if result.CfnLintResult != nil {
		totalIssues += len(result.CfnLintResult.Warnings)
	}
	rating, notes := scoring.ScoreCodeQuality(make([]string, totalIssues))
	score.CodeQuality.Rating = rating
	score.CodeQuality.Notes = notes

	// Output validity: cfn-lint results
	if result.CfnLintResult != nil {
		rating, notes := scoring.ScoreOutputValidity(
			len(result.CfnLintResult.Errors),
			len(result.CfnLintResult.Warnings),
		)
		score.OutputValidity.Rating = rating
		score.OutputValidity.Notes = notes
	} else {
		score.OutputValidity.Rating = scoring.RatingNone
		score.OutputValidity.Notes = "No template to validate"
	}

	// Question efficiency: N/A for validation, give full marks
	score.QuestionEfficiency.Rating = scoring.RatingExcellent
	score.QuestionEfficiency.Notes = "N/A for validation"

	return score
}

// runScenarioWithPersona runs the scenario with a specific persona.
// Returns (passed, error) where passed indicates if score >= 10.
func runScenarioWithPersona(scenario *Scenario, personaName string, flags *scenarioFlags) (bool, error) {
	ctx := context.Background()

	// Load persona
	persona, err := personas.Get(personaName)
	if err != nil {
		return false, err
	}

	// Load prompt for this persona
	promptPath := filepath.Join(scenario.PromptsDir, personaName+".md")
	promptData, err := os.ReadFile(promptPath)
	if err != nil {
		return false, fmt.Errorf("loading prompt: %w", err)
	}
	prompt := string(promptData)

	// Determine output directory
	outputDir := filepath.Join(scenario.ResultsDir, personaName)
	cleanupOutput := false
	if flags.saveResults || flags.saveExpected {
		if err := os.MkdirAll(outputDir, 0755); err != nil {
			return false, fmt.Errorf("creating results directory: %w", err)
		}
	} else {
		// Use temp directory
		outputDir, err = os.MkdirTemp("", "wetwire-scenario-*")
		if err != nil {
			return false, fmt.Errorf("creating temp directory: %w", err)
		}
		cleanupOutput = true
	}

	// Defer cleanup if needed (but not if we're saving expected)
	if cleanupOutput && !flags.saveExpected {
		defer os.RemoveAll(outputDir)
	}

	// Create session
	session := results.NewSession(persona.Name, scenario.Name)

	// Create AI developer with persona
	responder := agents.CreateDeveloperResponder("")
	aiDev := orchestrator.NewAIDeveloper(persona, responder)

	// Create runner agent
	runner, err := agents.NewRunnerAgent(agents.RunnerConfig{
		WorkDir:       outputDir,
		Session:       session,
		Developer:     aiDev,
		MaxLintCycles: 3,
	})
	if err != nil {
		return false, fmt.Errorf("creating runner: %w", err)
	}

	// Create orchestrator
	config := orchestrator.DefaultConfig()
	config.Persona = persona
	config.Scenario = scenario.Name
	config.InitialPrompt = prompt
	config.OutputDir = outputDir

	orch := orchestrator.New(config, aiDev, runner)

	// Run the session
	fmt.Printf("Running scenario with persona: %s\n", persona.Name)

	session, err = orch.Run(ctx)
	if err != nil {
		return false, fmt.Errorf("session failed: %w", err)
	}

	// Run cfn-lint on generated template if available
	var cfnErrors, cfnWarnings int
	if session.TemplateJSON != "" {
		// Save template to temp file for cfn-lint
		templatePath := filepath.Join(outputDir, "template.yaml")
		if err := os.WriteFile(templatePath, []byte(session.TemplateJSON), 0644); err == nil {
			cfnResult, err := validation.RunCfnLint(templatePath)
			if err == nil {
				cfnErrors = len(cfnResult.Errors)
				cfnWarnings = len(cfnResult.Warnings)

				// Print cfn-lint results
				fmt.Println("\n=== cfn-lint ===")
				if cfnResult.Passed {
					fmt.Println("Status: PASS")
				} else {
					fmt.Println("Status: FAIL")
				}
				fmt.Printf("Errors: %d, Warnings: %d\n", cfnErrors, cfnWarnings)
				for _, e := range cfnResult.Errors {
					fmt.Printf("  - %s\n", e)
				}
			}
		}
	}

	// Calculate score with cfn-lint results
	score := orch.CalculateScore(
		len(scenario.ExpectedFiles),
		len(session.GeneratedFiles),
		len(session.LintCycles) > 0 && session.LintCycles[len(session.LintCycles)-1].Passed,
		nil, cfnErrors, cfnWarnings,
	)

	passed := score.Total() >= 10

	// Write results if saving
	if flags.saveResults {
		writer := results.NewWriter(scenario.ResultsDir)
		if err := writer.Write(session); err != nil {
			return passed, fmt.Errorf("writing results: %w", err)
		}

		// Also write score summary
		scorePath := filepath.Join(outputDir, "score.json")
		scoreData, _ := json.MarshalIndent(score, "", "  ")
		if err := os.WriteFile(scorePath, scoreData, 0644); err != nil {
			return passed, fmt.Errorf("writing score: %w", err)
		}

		// Save template if available
		if session.TemplateJSON != "" {
			templatePath := filepath.Join(outputDir, "template.yaml")
			_ = os.WriteFile(templatePath, []byte(session.TemplateJSON), 0644)
		}

		// Save generated code to generated/ subdirectory
		generatedDir := filepath.Join(outputDir, "generated")
		if err := copyGeneratedFiles(outputDir, generatedDir, session.GeneratedFiles); err != nil {
			fmt.Printf("Warning: failed to copy generated files: %v\n", err)
		} else if len(session.GeneratedFiles) > 0 {
			fmt.Printf("Generated code saved to: %s\n", generatedDir)
		}
	}

	// Save as expected output if requested
	if flags.saveExpected && len(session.GeneratedFiles) > 0 {
		expectedDir := scenario.ExpectedDir

		// Remove existing expected directory
		if err := os.RemoveAll(expectedDir); err != nil {
			return passed, fmt.Errorf("removing existing expected: %w", err)
		}

		// Copy generated files to expected
		if err := copyGeneratedFiles(outputDir, expectedDir, session.GeneratedFiles); err != nil {
			return passed, fmt.Errorf("saving expected: %w", err)
		}

		fmt.Printf("Expected output saved to: %s\n", expectedDir)
	}

	// Print summary
	fmt.Printf("\n=== Results ===\n")
	fmt.Printf("Score: %d/15 (%s)\n", score.Total(), score.Threshold())
	fmt.Printf("Passed: %v\n", passed)

	if flags.saveResults {
		fmt.Printf("Results saved to: %s\n", outputDir)
	}

	return passed, nil
}

// copyGeneratedFiles copies generated files to a destination directory.
func copyGeneratedFiles(srcDir, dstDir string, files []string) error {
	if len(files) == 0 {
		return nil
	}

	if err := os.MkdirAll(dstDir, 0755); err != nil {
		return err
	}

	for _, file := range files {
		srcPath := filepath.Join(srcDir, file)
		dstPath := filepath.Join(dstDir, file)

		data, err := os.ReadFile(srcPath)
		if err != nil {
			// Try without the srcDir prefix (file might already be absolute or relative)
			data, err = os.ReadFile(file)
			if err != nil {
				continue // Skip files that can't be read
			}
		}

		if err := os.WriteFile(dstPath, data, 0644); err != nil {
			return err
		}
	}

	return nil
}
