"""CLI for wetwire-agent.

Commands:
    wetwire-agent design --domain aws           Interactive design session
    wetwire-agent test --domain aws             Automated test session
    wetwire-agent test --all                    Test all domains
    wetwire-agent run-scenario <path>           Run a specific scenario
    wetwire-agent validate-scenarios <path>     Validate all scenarios in a directory
"""

import argparse
import json
import sys
from pathlib import Path

from wetwire_agent.core.personas import PERSONAS, load_persona
from wetwire_agent.domains import get_domain, list_domains


def design_command(args: argparse.Namespace) -> int:
    """Run an interactive design session.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    from wetwire_agent.agents import run_interactive_design

    output_dir = Path.cwd()

    print(f"\n\033[1mwetwire-agent design\033[0m")
    print(f"\033[90mPackage will be created in: {output_dir}\033[0m\n")

    try:
        package_path, messages = run_interactive_design(
            initial_prompt=None,  # Will prompt interactively
            output_dir=output_dir,
        )

        if package_path:
            print(f"\n\033[32m✓ Package created at: {package_path}\033[0m")
            return 0
        else:
            print("\n\033[33m⚠ No package created or validation failed.\033[0m")
            return 1
    except KeyboardInterrupt:
        print("\n\n\033[33mSession cancelled.\033[0m")
        return 130


def test_command(args: argparse.Namespace) -> int:
    """Run an automated test session.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    if args.all:
        domains = list_domains()
        print(f"Testing all domains: {', '.join(domains)}")
    else:
        domains = [args.domain]
        print(f"Testing domain: {args.domain}")

    if args.persona:
        persona = load_persona(args.persona)
        print(f"Using persona: {persona.name} ({persona.description})")

    print("(Automated testing not yet implemented)")
    return 0


def run_ai_generation(args: argparse.Namespace) -> int:
    """Run AI generation for a scenario.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    import tempfile
    from wetwire_agent.agents import run_ai_scenario
    from wetwire_agent.runner import ScenarioRunner

    scenario_dir = args.scenario_path

    # Load persona
    persona_name = args.persona or "beginner"
    persona = load_persona(persona_name)

    # Load prompt (persona-specific or fallback to prompt.md)
    persona_prompt = scenario_dir / "prompts" / f"{persona_name}.md"
    if persona_prompt.exists():
        prompt = persona_prompt.read_text().strip()
    else:
        prompt = (scenario_dir / "prompt.md").read_text().strip()

    print(f"Generating with AI...")
    print(f"  Prompt: {prompt[:50]}...")
    print(f"  Persona: {persona_name}")
    print()

    # Create output directory
    output_dir = args.output or Path(tempfile.mkdtemp(prefix="wetwire-gen-"))

    try:
        # Run AI generation
        package_path, messages = run_ai_scenario(
            prompt=prompt,
            persona_name=persona_name,
            persona_instructions=persona.system_prompt,
            output_dir=output_dir,
        )

        # Print conversation
        print("=" * 60)
        print("CONVERSATION")
        print("=" * 60)
        for msg in messages:
            role = msg.role.upper()
            print(f"\n[{role}]")
            print(msg.content)
        print()

        if not package_path or not package_path.exists():
            print("ERROR: No package was generated", file=sys.stderr)
            return 1

        print(f"Package generated at: {package_path}")

        # Now validate the generated package
        print("\n" + "=" * 60)
        print("VALIDATION")
        print("=" * 60)

        # Create a temporary scenario with the generated package
        temp_scenario = Path(tempfile.mkdtemp(prefix="wetwire-validate-"))
        (temp_scenario / "prompt.md").write_text(prompt)

        # Copy generated package as expected
        import shutil
        expected_dir = temp_scenario / "expected"
        shutil.copytree(package_path, expected_dir)

        # Run validation
        runner = ScenarioRunner(temp_scenario, persona=persona_name)
        result = runner.run()

        # Print results
        print(f"\nScore: {result.score.total}/{result.score.max}")
        print("\nScore Breakdown:")
        print(f"  Completeness:        {result.score.completeness}/3")
        print(f"  Lint Quality:        {result.score.lint_quality}/3")
        print(f"  Code Quality:        {result.score.code_quality}/3")
        print(f"  Output Validity:     {result.score.output_validity}/3")
        print(f"  Question Efficiency: {result.score.question_efficiency}/3")

        # Print lint results
        print(f"\nLint Cycles: {len(result.lint_cycles)}")
        for i, cycle in enumerate(result.lint_cycles, 1):
            status = "PASS" if cycle.passed else "FAIL"
            print(f"  Cycle {i}: {status} ({len(cycle.issues)} issues)")

        # Print build result
        build_status = "SUCCESS" if result.build_result.success else "FAILED"
        print(f"\nBuild: {build_status}")

        # Save results if requested
        if args.save_results:
            # Save to results/<persona>/ directory
            results_dir = scenario_dir / "results" / persona_name
            results_dir.mkdir(parents=True, exist_ok=True)

            # Generate results.md
            results_md = runner.generate_results_md(result)

            # Add conversation log
            conv_log = "\n## Conversation Log\n\n```\n"
            for msg in messages:
                conv_log += f"{msg.role.upper()}: {msg.content}\n\n"
            conv_log += "```\n"

            results_md = results_md.replace("## Conversation Log", conv_log)

            results_file = results_dir / "results.md"
            results_file.write_text(results_md)
            print(f"\nResults saved to: {results_file}")

            # Save score.json
            score_file = results_dir / "score.json"
            score_file.write_text(json.dumps(result.score.to_dict(), indent=2))
            print(f"Score saved to: {score_file}")

            # Save generated template
            if result.build_result.success and result.build_result.template:
                template_file = results_dir / "template.yaml"
                template_file.write_text(result.build_result.template)
                print(f"Template saved to: {template_file}")

            # Save generated code
            if package_path and package_path.exists():
                generated_dir = results_dir / "generated"
                if generated_dir.exists():
                    shutil.rmtree(generated_dir)
                shutil.copytree(package_path, generated_dir)
                print(f"Generated code saved to: {generated_dir}")

            # Optionally save generated package as new expected
            if args.save_expected:
                expected_dest = scenario_dir / "expected"
                if expected_dest.exists():
                    shutil.rmtree(expected_dest)
                shutil.copytree(package_path, expected_dest)
                print(f"Expected output saved to: {expected_dest}")

        # Return success if score >= 10
        # Build summary for multi-persona runs
        summary = {
            "persona": persona_name,
            "score": result.score.total,
            "max": result.score.max,
            "passed": result.score.total >= 10,
            "lint_passed": result.lint_cycles and result.lint_cycles[0].passed,
            "cfn_lint_passed": result.cfn_lint_result.passed,
        }

        if result.score.total >= 10:
            print(f"\n✓ PASSED (score >= 10)")
            return 0, summary
        else:
            print(f"\n✗ FAILED (score < 10)")
            return 1, summary

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        # Return failure summary
        return 1, {
            "persona": persona_name,
            "score": 0,
            "max": 15,
            "passed": False,
            "lint_passed": False,
            "cfn_lint_passed": False,
        }


def list_command(args: argparse.Namespace) -> int:
    """List available resources.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    if args.resource == "domains":
        print("Available domains:")
        for name in list_domains():
            print(f"  - {name}")
    elif args.resource == "personas":
        print("Available personas:")
        for name, persona in PERSONAS.items():
            print(f"  - {name}: {persona.description}")
    elif args.resource == "prompts":
        if not args.domain:
            print("Error: --domain required for listing prompts", file=sys.stderr)
            return 1
        domain = get_domain(args.domain)
        print(f"Available prompts for {args.domain}:")
        for difficulty in ["simple", "medium", "complex", "adversarial"]:
            prompts = domain.get_prompts(difficulty)
            if prompts:
                print(f"\n  {difficulty.upper()}:")
                for p in prompts:
                    print(f"    - {p.name}: {p.description}")
    return 0


def run_single_scenario(
    scenario_dir: Path,
    persona: str,
    output_dir: Path | None,
    save_results: bool,
    generate: bool,
    args: argparse.Namespace,
) -> tuple[int, dict]:
    """Run a single scenario with a specific persona.

    Returns:
        Tuple of (exit_code, summary_dict)
    """
    from wetwire_agent.runner import ScenarioRunner

    # If --generate flag, use AI to generate the package
    if generate:
        # Update args with specific persona for AI generation
        args.persona = persona
        return run_ai_generation(args)

    runner = ScenarioRunner(scenario_dir, output_dir, persona=persona)
    result = runner.run()

    # Print summary
    print(f"\n{'='*50}")
    print(f"Scenario: {scenario_dir.name}")
    print(f"Persona: {result.persona}")
    print(f"Score: {result.score.total}/{result.score.max}")
    print(f"{'='*50}")

    # Print score breakdown
    print("\nScore Breakdown:")
    print(f"  Completeness:        {result.score.completeness}/3")
    print(f"  Lint Quality:        {result.score.lint_quality}/3")
    print(f"  Code Quality:        {result.score.code_quality}/3")
    print(f"  Output Validity:     {result.score.output_validity}/3")
    print(f"  Question Efficiency: {result.score.question_efficiency}/3")

    # Print lint results
    print(f"\nwetwire-aws Lint: {len(result.lint_cycles)} cycle(s)")
    for i, cycle in enumerate(result.lint_cycles, 1):
        status = "PASS" if cycle.passed else "FAIL"
        print(f"  Cycle {i}: {status} ({len(cycle.issues)} issues)")

    # Print build result
    build_status = "SUCCESS" if result.build_result.success else "FAILED"
    print(f"\nBuild: {build_status}")
    if result.build_result.template_path:
        print(f"  Template: {result.build_result.template_path}")

    # Print cfn-lint results
    cfn_status = "PASS" if result.cfn_lint_result.passed else "FAIL"
    print(f"\ncfn-lint: {cfn_status}")
    print(f"  Errors: {len(result.cfn_lint_result.errors)}")
    print(f"  Warnings: {len(result.cfn_lint_result.warnings)}")
    if result.cfn_lint_result.errors:
        for err in result.cfn_lint_result.errors[:5]:  # Show first 5
            print(f"    - {err}")
        if len(result.cfn_lint_result.errors) > 5:
            print(f"    ... and {len(result.cfn_lint_result.errors) - 5} more")

    # Generate results if requested
    if save_results:
        # Save to results/<persona>/ subdirectory
        results_dir = scenario_dir / "results" / result.persona
        results_dir.mkdir(parents=True, exist_ok=True)

        results_md = runner.generate_results_md(result)
        results_file = results_dir / "results.md"
        results_file.write_text(results_md)
        print(f"\nResults saved to: {results_file}")

        # Save score.json
        score_file = results_dir / "score.json"
        score_file.write_text(json.dumps(result.score.to_dict(), indent=2))
        print(f"Score saved to: {score_file}")

        # Save generated template
        if result.build_result.success and result.build_result.template:
            template_file = results_dir / "template.yaml"
            template_file.write_text(result.build_result.template)
            print(f"Template saved to: {template_file}")

        # Save generated code (only in generate mode, not validation mode)
        if generate and result.package_path and result.package_path.exists():
            import shutil
            generated_dir = results_dir / "generated"
            if generated_dir.exists():
                shutil.rmtree(generated_dir)
            shutil.copytree(result.package_path, generated_dir)
            print(f"Generated code saved to: {generated_dir}")

    # Build summary for multi-persona runs
    summary = {
        "persona": persona,
        "score": result.score.total,
        "max": result.score.max,
        "passed": result.score.total >= 10,
        "lint_passed": result.lint_cycles and result.lint_cycles[0].passed,
        "cfn_lint_passed": result.cfn_lint_result.passed,
    }

    # Return success if score >= 10 (passing threshold)
    if result.score.total >= 10:
        print(f"\n✓ PASSED (score >= 10)")
        return 0, summary
    else:
        print(f"\n✗ FAILED (score < 10)")
        return 1, summary


def run_scenario_command(args: argparse.Namespace) -> int:
    """Run a specific scenario.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    scenario_dir = args.scenario_path
    if not scenario_dir.exists():
        print(f"Error: Scenario not found: {scenario_dir}", file=sys.stderr)
        return 1

    # Check for prompts (either prompts/ directory or legacy prompt.md)
    has_prompts = (scenario_dir / "prompts").is_dir() or (scenario_dir / "prompt.md").exists()
    if not has_prompts:
        print(f"Error: No prompts/ directory or prompt.md in scenario: {scenario_dir}", file=sys.stderr)
        return 1

    # Handle --persona all
    if args.persona == "all":
        personas = list(PERSONAS.keys())
        print(f"Running scenario with all {len(personas)} personas: {', '.join(personas)}")
        print("=" * 60)

        summaries = []
        any_failed = False

        for persona in personas:
            print(f"\n>>> Running with persona: {persona}")
            exit_code, summary = run_single_scenario(
                scenario_dir=scenario_dir,
                persona=persona,
                output_dir=args.output,
                save_results=args.save_results,
                generate=args.generate,
                args=args,
            )
            summaries.append(summary)
            if exit_code != 0:
                any_failed = True

        # Print summary table
        print("\n" + "=" * 60)
        print("SUMMARY: All Personas")
        print("=" * 60)
        print(f"{'Persona':<15} {'Score':<10} {'Lint':<8} {'cfn-lint':<10} {'Status'}")
        print("-" * 60)
        for s in summaries:
            lint = "✓" if s.get("lint_passed") else "✗"
            cfn = "✓" if s.get("cfn_lint_passed") else "✗"
            status = "PASS" if s.get("passed") else "FAIL"
            print(f"{s['persona']:<15} {s['score']}/{s['max']:<7} {lint:<8} {cfn:<10} {status}")

        passed = sum(1 for s in summaries if s.get("passed"))
        print("-" * 60)
        print(f"Total: {passed}/{len(summaries)} passed")

        return 1 if any_failed else 0

    # Single persona run
    print(f"Running scenario: {scenario_dir.name}")
    exit_code, _ = run_single_scenario(
        scenario_dir=scenario_dir,
        persona=args.persona,
        output_dir=args.output,
        save_results=args.save_results,
        generate=args.generate,
        args=args,
    )
    return exit_code


def validate_scenarios_command(args: argparse.Namespace) -> int:
    """Validate all scenarios in a directory.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 if all pass, 1 if any fail)
    """
    from wetwire_agent.runner import ScenarioRunner

    scenarios_dir = args.scenarios_path
    if not scenarios_dir.exists():
        print(f"Error: Scenarios directory not found: {scenarios_dir}", file=sys.stderr)
        return 1

    # Find all scenarios (directories with prompt.md or prompts/ directory)
    scenarios = [
        d for d in scenarios_dir.iterdir()
        if d.is_dir() and ((d / "prompt.md").exists() or (d / "prompts").is_dir())
    ]

    if not scenarios:
        print(f"No scenarios found in: {scenarios_dir}", file=sys.stderr)
        return 1

    # Use persona from args or default to beginner
    persona = getattr(args, 'persona', None) or "beginner"

    print(f"Found {len(scenarios)} scenarios in {scenarios_dir}")
    print(f"Using persona: {persona}")
    print("=" * 60)

    results = []
    for scenario_dir in sorted(scenarios):
        print(f"\n{scenario_dir.name}...")

        runner = ScenarioRunner(scenario_dir, persona=persona)
        result = runner.run()
        results.append((scenario_dir.name, result))

        status = "✓" if result.score.total >= 10 else "✗"
        lint_status = "✓" if result.lint_cycles and result.lint_cycles[0].passed else "✗"
        cfn_status = "✓" if result.cfn_lint_result.passed else "✗"
        print(f"  {status} Score: {result.score.total}/{result.score.max} | lint:{lint_status} cfn-lint:{cfn_status}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, r in results if r.score.total >= 10)
    failed = len(results) - passed

    for name, result in results:
        status = "PASS" if result.score.total >= 10 else "FAIL"
        cfn = "✓" if result.cfn_lint_result.passed else f"✗({len(result.cfn_lint_result.errors)}E)"
        print(f"  {name}: {status} ({result.score.total}/{result.score.max}) cfn-lint:{cfn}")

    print(f"\nTotal: {passed} passed, {failed} failed")

    # Exit with failure if any scenario failed
    if args.fail_fast and failed > 0:
        return 1

    # In CI mode, fail if any scenario is below threshold
    if args.ci and failed > 0:
        return 1

    return 0 if failed == 0 else 1


def main() -> int:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="wetwire-agent",
        description="Testing and design orchestration for wetwire domain packages",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Design command
    design_parser = subparsers.add_parser(
        "design",
        help="Run an interactive design session",
    )
    design_parser.set_defaults(func=design_command)

    # Test command
    test_parser = subparsers.add_parser(
        "test",
        help="Run an automated test session",
    )
    test_parser.add_argument(
        "--domain",
        "-d",
        choices=list_domains(),
        help="Domain to test",
    )
    test_parser.add_argument(
        "--all",
        action="store_true",
        help="Test all domains",
    )
    test_parser.add_argument(
        "--persona",
        "-p",
        choices=list(PERSONAS.keys()),
        help="Persona to use for testing",
    )
    test_parser.add_argument(
        "--difficulty",
        choices=["simple", "medium", "complex", "adversarial"],
        help="Filter prompts by difficulty",
    )
    test_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output directory for results",
    )
    test_parser.set_defaults(func=test_command)

    # List command
    list_parser = subparsers.add_parser(
        "list",
        help="List available resources",
    )
    list_parser.add_argument(
        "resource",
        choices=["domains", "personas", "prompts"],
        help="Resource type to list",
    )
    list_parser.add_argument(
        "--domain",
        "-d",
        choices=list_domains(),
        help="Domain for filtering (required for prompts)",
    )
    list_parser.set_defaults(func=list_command)

    # Run scenario command
    run_scenario_parser = subparsers.add_parser(
        "run-scenario",
        help="Run a specific scenario",
    )
    run_scenario_parser.add_argument(
        "scenario_path",
        type=Path,
        help="Path to scenario directory (contains prompt.md)",
    )
    run_scenario_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output directory for generated package",
    )
    run_scenario_parser.add_argument(
        "--generate",
        "-g",
        action="store_true",
        help="Use AI to generate the package (requires ANTHROPIC_API_KEY)",
    )
    run_scenario_parser.add_argument(
        "--persona",
        "-p",
        choices=list(PERSONAS.keys()) + ["all"],
        default="beginner",
        help="Persona for AI developer (default: beginner). Use 'all' to run with all personas.",
    )
    run_scenario_parser.add_argument(
        "--save-results",
        action="store_true",
        help="Save results.md and score.json to scenario directory",
    )
    run_scenario_parser.add_argument(
        "--save-expected",
        action="store_true",
        help="Save generated package as new expected output (with --generate)",
    )
    run_scenario_parser.set_defaults(func=run_scenario_command)

    # Validate scenarios command
    validate_parser = subparsers.add_parser(
        "validate-scenarios",
        help="Validate all scenarios in a directory",
    )
    validate_parser.add_argument(
        "scenarios_path",
        type=Path,
        help="Path to scenarios directory",
    )
    validate_parser.add_argument(
        "--ci",
        action="store_true",
        help="CI mode: exit with failure if any scenario fails",
    )
    validate_parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first failure",
    )
    validate_parser.set_defaults(func=validate_scenarios_command)

    args = parser.parse_args()

    # Validate test command arguments
    if args.command == "test" and not args.all and not args.domain:
        parser.error("Either --domain or --all is required for test command")

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
