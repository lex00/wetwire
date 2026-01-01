package main

import (
	"fmt"

	"github.com/lex00/wetwire-agent/internal/personas"
	"github.com/spf13/cobra"
)

func newListCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "list <type>",
		Short: "List available resources",
		Long: `List available personas, domains, or scenarios.

Examples:
    wetwire-agent list personas
    wetwire-agent list domains`,
	}

	cmd.AddCommand(
		newListPersonasCmd(),
		newListDomainsCmd(),
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
