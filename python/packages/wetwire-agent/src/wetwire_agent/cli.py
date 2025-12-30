"""CLI for wetwire-agent.

Commands:
    wetwire-agent design --domain aws    Interactive design session
    wetwire-agent test --domain aws      Automated test session
    wetwire-agent test --all             Test all domains
"""

import argparse
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
    print(f"Starting design session for domain: {args.domain}")
    print("(Interactive design not yet implemented)")
    return 0


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
    design_parser.add_argument(
        "--domain",
        "-d",
        required=True,
        choices=list_domains(),
        help="Domain to use (e.g., aws)",
    )
    design_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output directory for generated package",
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

    args = parser.parse_args()

    # Validate test command arguments
    if args.command == "test" and not args.all and not args.domain:
        parser.error("Either --domain or --all is required for test command")

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
