package main

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/lex00/wetwire-agent/internal/agents"
	"github.com/lex00/wetwire-agent/internal/orchestrator"
	"github.com/lex00/wetwire-agent/internal/personas"
	"github.com/lex00/wetwire-agent/internal/results"
	"github.com/spf13/cobra"
)

// ANSI color codes for terminal output
const (
	colorReset  = "\033[0m"
	colorBold   = "\033[1m"
	colorGray   = "\033[90m"
	colorYellow = "\033[33m"
	colorGreen  = "\033[32m"
	colorRed    = "\033[31m"
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

If no prompt is provided, you will be prompted interactively.
If an existing wetwire-aws package is found in the output directory,
you can modify it instead of creating a new one.

Examples:
    wetwire-agent design "I need a bucket for logs"
    wetwire-agent design "Lambda function triggered by S3 uploads"
    wetwire-agent design                                           # prompts interactively
    wetwire-agent design -o ./myapp                                # use existing package

The Runner will ask clarifying questions as needed and generate
wetwire-aws code that produces valid CloudFormation templates.`,
		Args: cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			prompt := ""
			if len(args) > 0 {
				prompt = args[0]
			}
			return runDesign(prompt, outputDir)
		},
	}

	cmd.Flags().StringVarP(&outputDir, "output", "o", ".", "Output directory for generated files")

	return cmd
}

func runDesign(prompt, outputDir string) error {
	ctx := context.Background()
	reader := bufio.NewReader(os.Stdin)

	// Check for existing package
	existingPackage, existingFiles := detectExistingPackage(outputDir)
	if existingPackage != "" {
		fmt.Printf("%sFound existing package: %s%s\n", colorYellow, existingPackage, colorReset)
		if len(existingFiles) > 0 {
			fmt.Printf("%sFiles: %s%s\n", colorGray, strings.Join(existingFiles, ", "), colorReset)
		}
		fmt.Println()
	}

	// If no prompt provided, ask interactively
	if prompt == "" {
		if existingPackage != "" {
			fmt.Printf("%sWhat would you like to add or change?%s\n", colorBold, colorReset)
		} else {
			fmt.Printf("%sDescribe what infrastructure you need:%s\n", colorBold, colorReset)
		}
		fmt.Printf("%sType something:%s ", colorBold, colorReset)

		line, err := reader.ReadString('\n')
		if err != nil {
			return fmt.Errorf("reading prompt: %w", err)
		}
		prompt = strings.TrimSpace(line)

		if prompt == "" {
			return fmt.Errorf("no prompt provided")
		}
	}

	// Prefix prompt with existing package context if applicable
	if existingPackage != "" {
		prompt = fmt.Sprintf("[EXISTING PACKAGE: %s]\n[FILES: %s]\n\n%s",
			existingPackage,
			strings.Join(existingFiles, ", "),
			prompt)
	}

	// Create human developer with interactive continuation support
	humanDev := orchestrator.NewHumanDeveloper(func() (string, error) {
		line, err := reader.ReadString('\n')
		if err != nil {
			return "", err
		}
		return strings.TrimSpace(line), nil
	})

	// Create session
	session := results.NewSession("human", "interactive")

	// Create stream handler for real-time output
	streamHandler := func(text string) {
		fmt.Print(text)
	}

	// Create runner agent
	runner, err := agents.NewRunnerAgent(agents.RunnerConfig{
		WorkDir:       outputDir,
		Session:       session,
		Developer:     humanDev,
		MaxLintCycles: 3,
		StreamHandler: streamHandler,
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

	// Interactive continuation loop
	for {
		// Check if we have generated files (build succeeded)
		if len(session.GeneratedFiles) > 0 && session.TemplateJSON != "" {
			fmt.Printf("\n%sWhat's next?%s (type 'done' to exit): ", colorBold, colorReset)
			line, err := reader.ReadString('\n')
			if err != nil {
				break
			}
			response := strings.TrimSpace(line)

			if response == "" || strings.ToLower(response) == "done" ||
				strings.ToLower(response) == "quit" || strings.ToLower(response) == "exit" ||
				strings.ToLower(response) == "q" {
				fmt.Printf("\n%sSession ended.%s\n", colorYellow, colorReset)
				break
			}

			// Continue with new request
			config.InitialPrompt = response
			session, err = orch.Run(ctx)
			if err != nil {
				fmt.Printf("Error: %v\n", err)
				break
			}
		} else {
			// No successful build yet, just exit
			break
		}
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

// detectExistingPackage checks if a directory contains an existing wetwire-aws package.
// For Go packages, we look for a go.mod file or .go files with wetwire imports.
func detectExistingPackage(dir string) (packageName string, files []string) {
	// Check for go.mod
	goModPath := filepath.Join(dir, "go.mod")
	if _, err := os.Stat(goModPath); err == nil {
		// Read go.mod to get package name
		data, err := os.ReadFile(goModPath)
		if err == nil {
			lines := strings.Split(string(data), "\n")
			for _, line := range lines {
				if strings.HasPrefix(line, "module ") {
					packageName = strings.TrimPrefix(line, "module ")
					packageName = strings.TrimSpace(packageName)
					break
				}
			}
		}
	}

	// If no go.mod, check for main.go or any .go files with wetwire imports
	if packageName == "" {
		entries, err := os.ReadDir(dir)
		if err != nil {
			return "", nil
		}

		for _, entry := range entries {
			if entry.IsDir() || filepath.Ext(entry.Name()) != ".go" {
				continue
			}

			// Check if file contains wetwire imports
			filePath := filepath.Join(dir, entry.Name())
			data, err := os.ReadFile(filePath)
			if err != nil {
				continue
			}

			if strings.Contains(string(data), "wetwire-aws") {
				packageName = filepath.Base(dir)
				break
			}
		}
	}

	// If we found a package, list the .go files
	if packageName != "" {
		entries, err := os.ReadDir(dir)
		if err == nil {
			for _, entry := range entries {
				if !entry.IsDir() && filepath.Ext(entry.Name()) == ".go" {
					files = append(files, entry.Name())
				}
			}
		}
	}

	return packageName, files
}
