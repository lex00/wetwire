package main

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/lex00/wetwire-aws/internal/importer"
	"github.com/spf13/cobra"
)

func newImportCmd() *cobra.Command {
	var (
		outputDir      string
		packageName    string
		modulePath     string
		singleFile     bool
		withScaffold   bool
	)

	cmd := &cobra.Command{
		Use:   "import <template>",
		Short: "Import CloudFormation template to Go code",
		Long: `Import a CloudFormation YAML/JSON template and generate Go code.

Examples:
  # Import a template and generate Go package
  wetwire-aws import template.yaml -o ./infra

  # Import with custom package name
  wetwire-aws import template.yaml -o ./infra --package mystack

  # Generate a complete project with go.mod, cmd/main.go, .gitignore, CLAUDE.md
  wetwire-aws import template.yaml -o ./myproject --scaffold

  # Generate a single file instead of a package
  wetwire-aws import template.yaml -o ./infra --single-file`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			templatePath := args[0]

			// Parse template
			ir, err := importer.ParseTemplate(templatePath)
			if err != nil {
				return fmt.Errorf("failed to parse template: %w", err)
			}

			// Derive package name if not specified
			if packageName == "" {
				packageName = importer.DerivePackageName(templatePath)
			}

			// Generate code
			files := importer.GenerateCode(ir, packageName)

			// Add scaffold files if requested
			if withScaffold {
				if modulePath == "" {
					modulePath = packageName
				}
				scaffoldFiles := importer.GenerateTemplateFiles(packageName, modulePath)
				for filename, content := range scaffoldFiles {
					files[filename] = content
				}
			}

			// Determine output location
			if outputDir == "" {
				outputDir = "."
			}

			// Create output directory
			if err := os.MkdirAll(outputDir, 0755); err != nil {
				return fmt.Errorf("failed to create output directory: %w", err)
			}

			// Write files
			for filename, content := range files {
				outPath := filepath.Join(outputDir, filename)

				// Create parent directory if needed
				if err := os.MkdirAll(filepath.Dir(outPath), 0755); err != nil {
					return fmt.Errorf("failed to create directory for %s: %w", outPath, err)
				}

				if err := os.WriteFile(outPath, []byte(content), 0644); err != nil {
					return fmt.Errorf("failed to write %s: %w", outPath, err)
				}

				fmt.Printf("Generated: %s\n", outPath)
			}

			// Print summary
			fmt.Printf("\nImported %d resources, %d parameters, %d outputs\n",
				len(ir.Resources), len(ir.Parameters), len(ir.Outputs))

			if withScaffold {
				fmt.Println("\nScaffold files generated:")
				fmt.Println("  go.mod, cmd/main.go, .gitignore, CLAUDE.md")
			}

			return nil
		},
	}

	cmd.Flags().StringVarP(&outputDir, "output", "o", "", "Output directory (default: current directory)")
	cmd.Flags().StringVarP(&packageName, "package", "p", "", "Package name (default: derived from template filename)")
	cmd.Flags().StringVar(&modulePath, "module", "", "Go module path (default: same as package name)")
	cmd.Flags().BoolVar(&singleFile, "single-file", false, "Generate a single file instead of a package")
	cmd.Flags().BoolVar(&withScaffold, "scaffold", false, "Generate scaffold files (go.mod, cmd/main.go, .gitignore, CLAUDE.md)")

	return cmd
}
