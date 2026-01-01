package main

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/lex00/wetwire-agent/internal/agents"
	"github.com/lex00/wetwire-agent/internal/orchestrator"
	"github.com/lex00/wetwire-agent/internal/personas"
	"github.com/lex00/wetwire-agent/internal/results"
	"github.com/spf13/cobra"
)

func newDesignCmd() *cobra.Command {
	var (
		outputDir string
	)

	cmd := &cobra.Command{
		Use:   "design [prompt]",
		Short: "Start an interactive design session",
		Long: `Design starts an interactive session where you describe your infrastructure
needs and the AI Runner agent generates the code.

Examples:
    wetwire-agent design "I need a bucket for logs"
    wetwire-agent design "Lambda function triggered by S3 uploads"

The Runner will ask clarifying questions as needed and generate
wetwire-aws code that produces valid CloudFormation templates.`,
		Args: cobra.MinimumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return runDesign(args[0], outputDir)
		},
	}

	cmd.Flags().StringVarP(&outputDir, "output", "o", ".", "Output directory for generated files")

	return cmd
}

func runDesign(prompt, outputDir string) error {
	ctx := context.Background()

	// Create human developer (reads from stdin)
	reader := bufio.NewReader(os.Stdin)
	humanDev := orchestrator.NewHumanDeveloper(func() (string, error) {
		line, err := reader.ReadString('\n')
		if err != nil {
			return "", err
		}
		return strings.TrimSpace(line), nil
	})

	// Create session
	session := results.NewSession("human", "interactive")

	// Create runner agent
	runner, err := agents.NewRunnerAgent(agents.RunnerConfig{
		WorkDir:       outputDir,
		Session:       session,
		Developer:     humanDev,
		MaxLintCycles: 3,
	})
	if err != nil {
		return fmt.Errorf("creating runner: %w", err)
	}

	// Create orchestrator
	config := orchestrator.DefaultConfig()
	config.Persona = personas.Persona{Name: "human"}
	config.Scenario = "interactive"
	config.InitialPrompt = prompt
	config.OutputDir = outputDir

	orch := orchestrator.New(config, humanDev, runner)

	// Run the session
	fmt.Println("Starting design session...")
	fmt.Printf("Prompt: %s\n\n", prompt)

	session, err = orch.Run(ctx)
	if err != nil {
		return fmt.Errorf("session failed: %w", err)
	}

	// Write results
	writer := results.NewWriter(outputDir)
	if err := writer.Write(session); err != nil {
		return fmt.Errorf("writing results: %w", err)
	}

	fmt.Printf("\nSession complete! Results written to %s/\n", outputDir)
	fmt.Printf("Generated files: %v\n", session.GeneratedFiles)

	return nil
}
