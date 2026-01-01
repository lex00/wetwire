package main

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/lex00/wetwire-agent/internal/personas"
	"github.com/spf13/cobra"
)

func newListCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "list <type>",
		Short: "List available resources",
		Long: `List available personas, domains, prompts, or scenarios.

Examples:
    wetwire-agent list personas
    wetwire-agent list domains
    wetwire-agent list prompts --path ./testdata/scenarios`,
	}

	cmd.AddCommand(
		newListPersonasCmd(),
		newListDomainsCmd(),
		newListPromptsCmd(),
	)

	return cmd
}

func newListPersonasCmd() *cobra.Command {
	var verbose bool

	cmd := &cobra.Command{
		Use:   "personas",
		Short: "List available developer personas",
		Run: func(cmd *cobra.Command, args []string) {
			listPersonas(verbose)
		},
	}

	cmd.Flags().BoolVarP(&verbose, "verbose", "v", false, "Show detailed descriptions")

	return cmd
}

func listPersonas(verbose bool) {
	fmt.Println("Available Personas:")
	fmt.Println()

	for _, p := range personas.All() {
		if verbose {
			fmt.Printf("  %s\n", p.Name)
			fmt.Printf("    Description: %s\n", p.Description)
			fmt.Printf("    Expected behavior: %s\n\n", p.ExpectedBehavior)
		} else {
			fmt.Printf("  %-12s  %s\n", p.Name, p.Description)
		}
	}

	if !verbose {
		fmt.Println()
		fmt.Println("Use --verbose for detailed descriptions")
	}
}

func newListDomainsCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "domains",
		Short: "List available infrastructure domains",
		Run: func(cmd *cobra.Command, args []string) {
			listDomains()
		},
	}
}

func listDomains() {
	fmt.Println("Available Domains:")
	fmt.Println()

	domains := []struct {
		name        string
		cli         string
		description string
	}{
		{"aws", "wetwire-aws", "AWS CloudFormation resources"},
		// Future domains:
		// {"gcp", "wetwire-gcp", "Google Cloud Config Connector resources"},
		// {"azure", "wetwire-azure", "Azure ARM resources"},
		// {"k8s", "wetwire-k8s", "Kubernetes resources"},
	}

	for _, d := range domains {
		fmt.Printf("  %-10s  %-15s  %s\n", d.name, d.cli, d.description)
	}
}

func newListPromptsCmd() *cobra.Command {
	var scenariosPath string

	cmd := &cobra.Command{
		Use:   "prompts",
		Short: "List available prompts from scenarios",
		Long: `List available prompts from scenarios directory.

Shows all scenarios and the personas for which prompts are available.

Examples:
    wetwire-agent list prompts
    wetwire-agent list prompts --path ./testdata/scenarios`,
		Run: func(cmd *cobra.Command, args []string) {
			listPrompts(scenariosPath)
		},
	}

	cmd.Flags().StringVarP(&scenariosPath, "path", "p", "./testdata/scenarios", "Path to scenarios directory")

	return cmd
}

func listPrompts(scenariosPath string) {
	// Check if directory exists
	info, err := os.Stat(scenariosPath)
	if err != nil {
		fmt.Printf("Scenarios directory not found: %s\n", scenariosPath)
		fmt.Println("Use --path to specify the scenarios directory")
		return
	}
	if !info.IsDir() {
		fmt.Printf("Path is not a directory: %s\n", scenariosPath)
		return
	}

	// Find all scenarios
	entries, err := os.ReadDir(scenariosPath)
	if err != nil {
		fmt.Printf("Error reading directory: %v\n", err)
		return
	}

	fmt.Println("Available Prompts:")
	fmt.Println()

	found := false
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		scenarioDir := filepath.Join(scenariosPath, entry.Name())
		promptsDir := filepath.Join(scenarioDir, "prompts")

		// Check for prompts/ directory
		if !dirExists(promptsDir) {
			continue
		}

		// List prompts for this scenario
		promptEntries, err := os.ReadDir(promptsDir)
		if err != nil {
			continue
		}

		var promptNames []string
		for _, pe := range promptEntries {
			if !pe.IsDir() && filepath.Ext(pe.Name()) == ".md" {
				name := pe.Name()[:len(pe.Name())-3] // Remove .md
				promptNames = append(promptNames, name)
			}
		}

		if len(promptNames) > 0 {
			found = true
			fmt.Printf("  %s:\n", entry.Name())
			for _, name := range promptNames {
				fmt.Printf("    - %s\n", name)
			}
			fmt.Println()
		}
	}

	if !found {
		fmt.Println("  No scenarios with prompts found")
		fmt.Printf("  (searched in: %s)\n", scenariosPath)
	}
}
