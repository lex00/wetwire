package main

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/lex00/wetwire-agent/internal/scoring"
	"github.com/lex00/wetwire-agent/internal/validation"
	"github.com/spf13/cobra"
)

func newValidateScenariosCmd() *cobra.Command {
	var (
		ciMode   bool
		failFast bool
	)

	cmd := &cobra.Command{
		Use:   "validate-scenarios <scenarios-path>",
		Short: "Validate all scenarios in a directory",
		Long: `Validate all scenarios in a directory by running the validation pipeline
on each scenario's expected/ directory.

This command is useful for CI/CD pipelines to ensure all scenarios pass validation.

Examples:
    wetwire-agent validate-scenarios ./testdata/scenarios
    wetwire-agent validate-scenarios ./testdata/scenarios --ci
    wetwire-agent validate-scenarios ./testdata/scenarios --fail-fast`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return runValidateScenarios(args[0], ciMode, failFast)
		},
	}

	cmd.Flags().BoolVar(&ciMode, "ci", false, "CI mode: exit with failure if any scenario fails")
	cmd.Flags().BoolVar(&failFast, "fail-fast", false, "Stop on first failure")

	return cmd
}

// scenarioResult holds the validation result for a single scenario.
type scenarioResult struct {
	Name       string
	Score      *scoring.Score
	LintPassed bool
	CfnPassed  bool
	CfnErrors  int
	Passed     bool
	Error      error
}

func runValidateScenarios(scenariosPath string, ciMode, failFast bool) error {
	// Check if directory exists
	info, err := os.Stat(scenariosPath)
	if err != nil {
		return fmt.Errorf("scenarios directory not found: %w", err)
	}
	if !info.IsDir() {
		return fmt.Errorf("path must be a directory: %s", scenariosPath)
	}

	// Find all scenarios (directories with expected/ subdirectory or prompts/ directory)
	entries, err := os.ReadDir(scenariosPath)
	if err != nil {
		return fmt.Errorf("reading scenarios directory: %w", err)
	}

	var scenarios []string
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		scenarioDir := filepath.Join(scenariosPath, entry.Name())

		// Check for expected/ directory or prompts/ directory
		expectedDir := filepath.Join(scenarioDir, "expected")
		promptsDir := filepath.Join(scenarioDir, "prompts")

		hasExpected := dirExists(expectedDir)
		hasPrompts := dirExists(promptsDir)

		if hasExpected || hasPrompts {
			scenarios = append(scenarios, entry.Name())
		}
	}

	if len(scenarios) == 0 {
		return fmt.Errorf("no scenarios found in: %s", scenariosPath)
	}

	// Sort scenarios for consistent output
	sort.Strings(scenarios)

	fmt.Printf("Found %d scenarios in %s\n", len(scenarios), scenariosPath)
	fmt.Println(strings.Repeat("=", 60))

	// Run validation on each scenario
	var results []scenarioResult

	for _, scenarioName := range scenarios {
		scenarioDir := filepath.Join(scenariosPath, scenarioName)
		expectedDir := filepath.Join(scenarioDir, "expected")

		fmt.Printf("\n%s...\n", scenarioName)

		result := scenarioResult{
			Name: scenarioName,
		}

		// Check if expected/ directory exists
		if !dirExists(expectedDir) {
			result.Error = fmt.Errorf("no expected/ directory")
			result.Passed = false
			fmt.Printf("  ✗ No expected/ directory\n")
			results = append(results, result)

			if failFast {
				break
			}
			continue
		}

		// Create temp directory for validation output
		tempDir, err := os.MkdirTemp("", "wetwire-validate-*")
		if err != nil {
			result.Error = err
			result.Passed = false
			fmt.Printf("  ✗ Error: %v\n", err)
			results = append(results, result)

			if failFast {
				break
			}
			continue
		}

		// Run validation pipeline
		valResult, err := validation.ValidatePackage(expectedDir, tempDir)
		os.RemoveAll(tempDir) // Clean up

		if err != nil {
			result.Error = err
			result.Passed = false
			fmt.Printf("  ✗ Error: %v\n", err)
			results = append(results, result)

			if failFast {
				break
			}
			continue
		}

		// Calculate score
		result.LintPassed = valResult.LintResult.Passed
		result.CfnPassed = valResult.CfnLintResult.Passed
		result.CfnErrors = len(valResult.CfnLintResult.Errors)

		// Count expected files for completeness scoring
		expectedFiles := countGoFiles(expectedDir)

		result.Score = calculateScenarioScore(scenarioName, valResult, expectedFiles)
		result.Passed = result.Score.Total() >= 10

		// Print result
		status := "✓"
		if !result.Passed {
			status = "✗"
		}
		lintStatus := "✓"
		if !result.LintPassed {
			lintStatus = "✗"
		}
		cfnStatus := "✓"
		if !result.CfnPassed {
			cfnStatus = "✗"
		}

		fmt.Printf("  %s Score: %d/15 | lint:%s cfn-lint:%s\n",
			status, result.Score.Total(), lintStatus, cfnStatus)

		results = append(results, result)

		if failFast && !result.Passed {
			break
		}
	}

	// Print summary
	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("SUMMARY")
	fmt.Println(strings.Repeat("=", 60))

	passed := 0
	failed := 0

	for _, r := range results {
		status := "PASS"
		if !r.Passed {
			status = "FAIL"
			failed++
		} else {
			passed++
		}

		cfnInfo := "✓"
		if !r.CfnPassed {
			cfnInfo = fmt.Sprintf("✗(%dE)", r.CfnErrors)
		}

		if r.Score != nil {
			fmt.Printf("  %s: %s (%d/15) cfn-lint:%s\n", r.Name, status, r.Score.Total(), cfnInfo)
		} else if r.Error != nil {
			fmt.Printf("  %s: %s (error: %v)\n", r.Name, status, r.Error)
		} else {
			fmt.Printf("  %s: %s\n", r.Name, status)
		}
	}

	fmt.Printf("\nTotal: %d passed, %d failed\n", passed, failed)

	// Determine exit code
	if failed > 0 && (ciMode || failFast) {
		return fmt.Errorf("%d scenario(s) failed", failed)
	}

	if failed > 0 {
		// Return error but with different message for non-CI mode
		os.Exit(1)
	}

	return nil
}

// calculateScenarioScore calculates a score for a scenario validation.
func calculateScenarioScore(name string, result *validation.ValidationResult, expectedFiles int) *scoring.Score {
	score := scoring.NewScore("validation", name)

	// Completeness: Check if build succeeded
	if result.BuildResult.Success && result.BuildResult.Template != "" {
		rating, notes := scoring.ScoreCompleteness(expectedFiles, expectedFiles)
		score.Completeness.Rating = rating
		score.Completeness.Notes = notes
	} else {
		score.Completeness.Rating = scoring.RatingNone
		score.Completeness.Notes = "Build failed"
	}

	// Lint quality
	if result.LintResult.Passed {
		score.LintQuality.Rating = scoring.RatingExcellent
		score.LintQuality.Notes = "Passed"
	} else {
		score.LintQuality.Rating = scoring.RatingNone
		score.LintQuality.Notes = fmt.Sprintf("%d lint issues", len(result.LintResult.Issues))
	}

	// Code quality
	totalIssues := len(result.LintResult.Issues)
	if result.CfnLintResult != nil {
		totalIssues += len(result.CfnLintResult.Warnings)
	}
	rating, notes := scoring.ScoreCodeQuality(make([]string, totalIssues))
	score.CodeQuality.Rating = rating
	score.CodeQuality.Notes = notes

	// Output validity
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

	// Question efficiency: N/A for validation
	score.QuestionEfficiency.Rating = scoring.RatingExcellent
	score.QuestionEfficiency.Notes = "N/A"

	return score
}

// dirExists checks if a directory exists.
func dirExists(path string) bool {
	info, err := os.Stat(path)
	if err != nil {
		return false
	}
	return info.IsDir()
}

// countGoFiles counts .go files in a directory.
func countGoFiles(dir string) int {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return 0
	}

	count := 0
	for _, e := range entries {
		if !e.IsDir() && filepath.Ext(e.Name()) == ".go" {
			count++
		}
	}
	return count
}
