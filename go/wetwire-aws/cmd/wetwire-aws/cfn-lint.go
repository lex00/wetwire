package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/lex00/cfn-lint-go/pkg/lint"
	"github.com/spf13/cobra"
)

func newCfnLintCmd() *cobra.Command {
	var (
		outputFormat string
		ignoreRules  []string
		regions      []string
	)

	cmd := &cobra.Command{
		Use:   "cfn-lint [templates...]",
		Short: "Lint CloudFormation templates using cfn-lint-go",
		Long: `Lint CloudFormation YAML/JSON templates for common issues.

This command uses cfn-lint-go to validate CloudFormation templates against
AWS CloudFormation best practices and rules.

Examples:
    wetwire-aws cfn-lint template.yaml
    wetwire-aws cfn-lint *.yaml --format json
    wetwire-aws cfn-lint template.yaml --ignore-rules E3012,W2001`,
		Args: cobra.MinimumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return runCfnLint(args, outputFormat, ignoreRules, regions)
		},
	}

	cmd.Flags().StringVarP(&outputFormat, "format", "f", "text", "Output format: text or json")
	cmd.Flags().StringSliceVar(&ignoreRules, "ignore-rules", nil, "Rule IDs to ignore (comma-separated)")
	cmd.Flags().StringSliceVar(&regions, "regions", nil, "AWS regions to validate against")

	return cmd
}

func runCfnLint(templates []string, format string, ignoreRules, regions []string) error {
	linter := lint.New(lint.Options{
		IgnoreRules: ignoreRules,
		Regions:     regions,
	})

	var allMatches []lint.Match
	var hasErrors bool

	for _, tmpl := range templates {
		matches, err := linter.LintFile(tmpl)
		if err != nil {
			return fmt.Errorf("failed to lint %s: %w", tmpl, err)
		}
		allMatches = append(allMatches, matches...)

		// Check for errors
		for _, m := range matches {
			if m.Level == "Error" {
				hasErrors = true
			}
		}
	}

	return outputCfnLintResult(allMatches, format, hasErrors)
}

func outputCfnLintResult(matches []lint.Match, format string, hasErrors bool) error {
	switch format {
	case "json":
		data, err := json.MarshalIndent(matches, "", "  ")
		if err != nil {
			return err
		}
		fmt.Println(string(data))

	case "text":
		if len(matches) == 0 {
			fmt.Println("No issues found.")
			return nil
		}

		for _, m := range matches {
			// Format: filename:line:column: level rule-id message
			path := formatPath(m.Location.Path)
			fmt.Printf("%s:%d:%d: %s %s %s",
				m.Location.Filename,
				m.Location.Start.LineNumber,
				m.Location.Start.ColumnNumber,
				m.Level,
				m.Rule.ID,
				m.Message)
			if path != "" {
				fmt.Printf(" [%s]", path)
			}
			fmt.Println()
		}

	default:
		return fmt.Errorf("unknown format: %s", format)
	}

	if hasErrors {
		os.Exit(2) // Exit code 2 for errors found
	}

	return nil
}

func formatPath(path []any) string {
	if len(path) == 0 {
		return ""
	}
	parts := make([]string, len(path))
	for i, p := range path {
		parts[i] = fmt.Sprintf("%v", p)
	}
	return strings.Join(parts, "/")
}
