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
	"github.com/spf13/cobra"
)

func newRunScenarioCmd() *cobra.Command {
	var (
		personaName  string
		generate     bool
		saveResults  bool
	)

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
    wetwire-agent run-scenario ./scenarios/s3_log_bucket --persona all --save-results`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return runScenario(args[0], personaName, generate, saveResults)
		},
	}

	cmd.Flags().StringVarP(&personaName, "persona", "p", "", "Persona to use (or 'all')")
	cmd.Flags().BoolVar(&generate, "generate", false, "Generate code using AI (otherwise just validate expected/)")
	cmd.Flags().BoolVar(&saveResults, "save-results", false, "Save results to scenario results/ directory")

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

func runScenario(scenarioPath, personaName string, generate, saveResults bool) error {
	scenario, err := loadScenario(scenarioPath)
	if err != nil {
		return err
	}

	fmt.Printf("Scenario: %s\n", scenario.Name)
	fmt.Printf("Expected files: %v\n", scenario.ExpectedFiles)
	fmt.Printf("Available personas: %v\n\n", scenario.AvailablePersonas)

	if !generate {
		// Just validate the expected directory
		return validateExpected(scenario)
	}

	// Run with AI generation
	if personaName == "" {
		return fmt.Errorf("--persona required when using --generate")
	}

	if personaName == "all" {
		for _, p := range scenario.AvailablePersonas {
			fmt.Printf("\n=== Running persona: %s ===\n", p)
			if err := runScenarioWithPersona(scenario, p, saveResults); err != nil {
				fmt.Printf("Error: %v\n", err)
			}
		}
		return nil
	}

	return runScenarioWithPersona(scenario, personaName, saveResults)
}

func validateExpected(scenario *Scenario) error {
	fmt.Println("Validating expected/ directory...")

	// Run wetwire-aws lint on expected directory
	// (This would shell out to the CLI)
	fmt.Printf("Would run: wetwire-aws lint %s\n", scenario.ExpectedDir)
	fmt.Printf("Would run: wetwire-aws build %s\n", scenario.ExpectedDir)

	fmt.Println("Validation complete (placeholder)")
	return nil
}

func runScenarioWithPersona(scenario *Scenario, personaName string, saveResults bool) error {
	ctx := context.Background()

	// Load persona
	persona, err := personas.Get(personaName)
	if err != nil {
		return err
	}

	// Load prompt for this persona
	promptPath := filepath.Join(scenario.PromptsDir, personaName+".md")
	promptData, err := os.ReadFile(promptPath)
	if err != nil {
		return fmt.Errorf("loading prompt: %w", err)
	}
	prompt := string(promptData)

	// Determine output directory
	outputDir := filepath.Join(scenario.ResultsDir, personaName)
	if saveResults {
		if err := os.MkdirAll(outputDir, 0755); err != nil {
			return fmt.Errorf("creating results directory: %w", err)
		}
	} else {
		// Use temp directory
		outputDir, err = os.MkdirTemp("", "wetwire-scenario-*")
		if err != nil {
			return fmt.Errorf("creating temp directory: %w", err)
		}
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
		return fmt.Errorf("creating runner: %w", err)
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
		return fmt.Errorf("session failed: %w", err)
	}

	// Calculate score
	score := orch.CalculateScore(
		len(scenario.ExpectedFiles),
		len(session.GeneratedFiles),
		len(session.LintCycles) > 0 && session.LintCycles[len(session.LintCycles)-1].Passed,
		nil, 0, 0,
	)

	// Write results if saving
	if saveResults {
		writer := results.NewWriter(scenario.ResultsDir)
		if err := writer.Write(session); err != nil {
			return fmt.Errorf("writing results: %w", err)
		}

		// Also write score summary
		scorePath := filepath.Join(outputDir, "score.json")
		scoreData, _ := json.MarshalIndent(score, "", "  ")
		if err := os.WriteFile(scorePath, scoreData, 0644); err != nil {
			return fmt.Errorf("writing score: %w", err)
		}
	}

	// Print summary
	fmt.Printf("\n=== Results ===\n")
	fmt.Printf("Score: %d/15 (%s)\n", score.Total(), score.Threshold())
	fmt.Printf("Passed: %v\n", score.Passed())

	if saveResults {
		fmt.Printf("Results saved to: %s\n", outputDir)
	}

	return nil
}
