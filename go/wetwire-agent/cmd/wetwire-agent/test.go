package main

import (
	"context"
	"fmt"
	"os"

	"github.com/lex00/wetwire-agent/internal/agents"
	"github.com/lex00/wetwire-agent/internal/orchestrator"
	"github.com/lex00/wetwire-agent/internal/personas"
	"github.com/lex00/wetwire-agent/internal/results"
	"github.com/spf13/cobra"
)

func newTestCmd() *cobra.Command {
	var (
		persona   string
		outputDir string
		prompt    string
		domain    string
	)

	cmd := &cobra.Command{
		Use:   "test",
		Short: "Run a test session with an AI developer persona",
		Long: `Test runs an automated session where an AI Developer persona
provides requirements and the Runner generates code.

This is used for testing the Runner's capabilities with different
user types (beginner, expert, terse, verbose, etc.).

Examples:
    wetwire-agent test --persona beginner --prompt "I need a bucket"
    wetwire-agent test --persona expert --prompt "S3 with AES-256 SSE-S3"
    wetwire-agent test --persona all --prompt "log bucket"
    wetwire-agent test --domain aws --prompt "S3 bucket with encryption"`,
		RunE: func(cmd *cobra.Command, args []string) error {
			return runTest(persona, prompt, outputDir, domain)
		},
	}

	cmd.Flags().StringVarP(&persona, "persona", "p", "beginner", "Persona to use (beginner, intermediate, expert, terse, verbose, all)")
	cmd.Flags().StringVarP(&outputDir, "output", "o", ".", "Output directory for results")
	cmd.Flags().StringVar(&prompt, "prompt", "", "Initial prompt for the developer")
	cmd.Flags().StringVarP(&domain, "domain", "d", "aws", "Infrastructure domain (aws)")
	_ = cmd.MarkFlagRequired("prompt") // Flag defined above, safe to ignore

	return cmd
}

func runTest(personaName, prompt, outputDir, domain string) error {
	ctx := context.Background()

	// Validate domain
	validDomains := map[string]bool{"aws": true}
	if !validDomains[domain] {
		return fmt.Errorf("unsupported domain: %s (available: aws)", domain)
	}

	fmt.Printf("Domain: %s\n", domain)

	// Handle "all" personas
	if personaName == "all" {
		for _, p := range personas.All() {
			fmt.Printf("\n=== Running with persona: %s ===\n", p.Name)
			if err := runTestWithPersona(ctx, p, prompt, outputDir); err != nil {
				fmt.Printf("Error with %s: %v\n", p.Name, err)
			}
		}
		return nil
	}

	// Get the persona
	persona, err := personas.Get(personaName)
	if err != nil {
		return err
	}

	return runTestWithPersona(ctx, persona, prompt, outputDir)
}

func runTestWithPersona(ctx context.Context, persona personas.Persona, prompt, outputDir string) error {
	// Create session
	session := results.NewSession(persona.Name, "test")

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
	config.Scenario = "test"
	config.InitialPrompt = prompt
	config.OutputDir = outputDir

	orch := orchestrator.New(config, aiDev, runner)

	// Run the session
	fmt.Printf("Running test with persona: %s\n", persona.Name)
	fmt.Printf("Prompt: %s\n\n", prompt)

	session, err = orch.Run(ctx)
	if err != nil {
		return fmt.Errorf("session failed: %w", err)
	}

	// Calculate score (with placeholder values for now)
	score := orch.CalculateScore(
		1,                          // expected resources
		len(session.GeneratedFiles), // actual resources
		len(session.LintCycles) > 0 && session.LintCycles[len(session.LintCycles)-1].Passed,
		nil, // code issues
		0,   // cfn errors
		0,   // cfn warnings
	)

	// Write results
	writer := results.NewWriter(outputDir)
	if err := writer.Write(session); err != nil {
		return fmt.Errorf("writing results: %w", err)
	}

	// Print summary
	fmt.Printf("\n=== Results ===\n")
	fmt.Printf("Score: %d/15 (%s)\n", score.Total(), score.Threshold())
	fmt.Printf("Questions asked: %d\n", len(session.Questions))
	fmt.Printf("Lint cycles: %d\n", len(session.LintCycles))
	fmt.Printf("Generated files: %v\n", session.GeneratedFiles)
	fmt.Printf("Results written to: %s/%s/\n", outputDir, persona.Name)

	if !score.Passed() {
		os.Exit(2)
	}

	return nil
}
