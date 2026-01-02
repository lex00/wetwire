// Command wetwire-agent orchestrates AI agents for infrastructure code generation.
//
// Usage:
//
//	wetwire-agent design "I need a bucket for logs"     Interactive design session
//	wetwire-agent test --persona beginner               Run test with AI developer
//	wetwire-agent run-scenario ./scenarios/s3_bucket    Run a specific scenario
//	wetwire-agent list personas                         List available personas
package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var version = "0.2.2"

func main() {
	rootCmd := &cobra.Command{
		Use:   "wetwire-agent",
		Short: "AI-powered infrastructure code generation",
		Long: `wetwire-agent orchestrates AI agents for infrastructure code generation and testing.

It supports two modes:
  - Interactive design: Human provides requirements, AI generates code
  - Automated testing: AI personas simulate different user types

The two-agent pattern:
  - Developer: Provides requirements (human or AI persona)
  - Runner: Generates code, asks questions, runs lint cycles`,
	}

	rootCmd.AddCommand(
		newDesignCmd(),
		newTestCmd(),
		newRunScenarioCmd(),
		newValidateScenariosCmd(),
		newListCmd(),
		newVersionCmd(),
	)

	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func newVersionCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "version",
		Short: "Show version information",
		Run: func(cmd *cobra.Command, args []string) {
			fmt.Printf("wetwire-agent %s\n", version)
		},
	}
}
