package main

import (
	"encoding/json"
	"fmt"
	"os"

	wetwire "github.com/lex00/wetwire-aws"
	"github.com/lex00/wetwire-aws/internal/discover"
	"github.com/spf13/cobra"
)

func newLintCmd() *cobra.Command {
	var (
		outputFormat string
		fix          bool
	)

	cmd := &cobra.Command{
		Use:   "lint [packages...]",
		Short: "Check Go packages for issues",
		Long: `Lint checks Go packages containing CloudFormation resources for common issues.

Examples:
    wetwire-aws lint ./infra/...
    wetwire-aws lint ./infra/... --fix`,
		Args: cobra.MinimumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return runLint(args, outputFormat, fix)
		},
	}

	cmd.Flags().StringVarP(&outputFormat, "format", "f", "text", "Output format: text or json")
	cmd.Flags().BoolVar(&fix, "fix", false, "Automatically fix issues where possible")

	return cmd
}

func runLint(packages []string, format string, fix bool) error {
	// Discover resources (also validates references)
	result, err := discover.Discover(discover.Options{
		Packages: packages,
	})
	if err != nil {
		return fmt.Errorf("lint failed: %w", err)
	}

	// Convert discovery errors to lint issues
	var issues []wetwire.LintIssue
	for _, e := range result.Errors {
		issues = append(issues, wetwire.LintIssue{
			Severity: "error",
			Message:  e.Error(),
			Rule:     "undefined-reference",
		})
	}

	// TODO: Add more lint rules:
	// - Hardcoded strings that should be parameters
	// - Missing required properties
	// - Deprecated resource types
	// - Security best practices (public S3 buckets, etc.)

	lintResult := wetwire.LintResult{
		Success: len(issues) == 0,
		Issues:  issues,
	}

	return outputLintResult(lintResult, format)
}

func outputLintResult(result wetwire.LintResult, format string) error {
	switch format {
	case "json":
		data, err := json.MarshalIndent(result, "", "  ")
		if err != nil {
			return err
		}
		fmt.Println(string(data))

	case "text":
		if result.Success {
			fmt.Println("No issues found.")
			return nil
		}

		for _, issue := range result.Issues {
			severity := issue.Severity
			if issue.File != "" {
				fmt.Printf("%s:%d:%d: %s: %s [%s]\n",
					issue.File, issue.Line, issue.Column,
					severity, issue.Message, issue.Rule)
			} else {
				fmt.Printf("%s: %s [%s]\n", severity, issue.Message, issue.Rule)
			}
		}

	default:
		return fmt.Errorf("unknown format: %s", format)
	}

	if !result.Success {
		os.Exit(2) // Exit code 2 for issues found
	}

	return nil
}
