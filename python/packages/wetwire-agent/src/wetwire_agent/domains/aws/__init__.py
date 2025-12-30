"""AWS domain testing configuration.

This module provides AWS-specific configuration for the agent workflow:
- AWS prompt library organized by difficulty
- Runner implementation that uses wetwire-aws CLI
- Domain-specific validation
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wetwire_agent.core.orchestrator import RunnerProtocol


@dataclass
class Prompt:
    """A testing prompt for AWS infrastructure generation."""

    name: str
    description: str
    prompt: str
    difficulty: str  # simple, medium, complex, adversarial
    expected_resources: list[str]
    expected_questions: int


# Prompt library organized by difficulty
PROMPTS: dict[str, list[Prompt]] = {
    "simple": [
        Prompt(
            name="s3_bucket",
            description="Simple S3 bucket",
            prompt="Create an S3 bucket for storing application logs",
            difficulty="simple",
            expected_resources=["AWS::S3::Bucket"],
            expected_questions=0,
        ),
        Prompt(
            name="iam_role",
            description="Basic IAM role",
            prompt="Create an IAM role for Lambda execution",
            difficulty="simple",
            expected_resources=["AWS::IAM::Role"],
            expected_questions=1,
        ),
    ],
    "medium": [
        Prompt(
            name="vpc_basic",
            description="VPC with subnets",
            prompt="Create a VPC with 2 private subnets across 2 AZs",
            difficulty="medium",
            expected_resources=["AWS::EC2::VPC", "AWS::EC2::Subnet", "AWS::EC2::Subnet"],
            expected_questions=2,
        ),
        Prompt(
            name="lambda_s3",
            description="Lambda triggered by S3",
            prompt="Create a Lambda function that processes files uploaded to S3",
            difficulty="medium",
            expected_resources=[
                "AWS::Lambda::Function",
                "AWS::S3::Bucket",
                "AWS::IAM::Role",
            ],
            expected_questions=2,
        ),
    ],
    "complex": [
        Prompt(
            name="autoscaled_ec2",
            description="Autoscaled EC2 in private VPC",
            prompt=(
                "Build an autoscaled EC2 instance in a private VPC with NAT Gateway "
                "for outbound internet access"
            ),
            difficulty="complex",
            expected_resources=[
                "AWS::EC2::VPC",
                "AWS::EC2::Subnet",
                "AWS::EC2::NatGateway",
                "AWS::EC2::InternetGateway",
                "AWS::AutoScaling::AutoScalingGroup",
                "AWS::AutoScaling::LaunchConfiguration",
            ],
            expected_questions=3,
        ),
    ],
    "adversarial": [
        Prompt(
            name="too_ambiguous",
            description="Intentionally vague prompt",
            prompt="Create a thing that stores data",
            difficulty="adversarial",
            expected_resources=[],
            expected_questions=5,
        ),
        Prompt(
            name="impossible",
            description="Impossible constraint",
            prompt="Create an EC2 instance with 1TB of RAM",
            difficulty="adversarial",
            expected_resources=[],
            expected_questions=0,
        ),
    ],
}


class AwsRunner(RunnerProtocol):
    """AWS-specific Runner implementation.

    Uses wetwire-aws CLI for:
    - Package initialization (wetwire-aws init)
    - Linting (wetwire-aws lint)
    - Template validation (wetwire-aws build --validate)
    """

    def __init__(self, work_dir: Path) -> None:
        """Initialize AWS runner.

        Args:
            work_dir: Working directory for package generation
        """
        self.work_dir = work_dir
        self._complete = False

    def process(self, message: str) -> str:
        """Process a message and return response or question."""
        # TODO: Implement using Claude API and wetwire-aws CLI
        raise NotImplementedError("AwsRunner.process() not yet implemented")

    def is_complete(self) -> bool:
        """Check if the Runner has completed its work."""
        return self._complete


@dataclass
class AwsDomain:
    """AWS domain configuration."""

    name: str = "aws"
    cli_command: str = "wetwire-aws"

    def get_prompts(self, difficulty: str | None = None) -> list[Prompt]:
        """Get prompts, optionally filtered by difficulty.

        Args:
            difficulty: Filter by difficulty level

        Returns:
            List of prompts
        """
        if difficulty:
            return PROMPTS.get(difficulty, [])
        return [p for prompts in PROMPTS.values() for p in prompts]

    def create_runner(self, work_dir: Path) -> AwsRunner:
        """Create an AWS runner.

        Args:
            work_dir: Working directory for package generation

        Returns:
            Configured AwsRunner
        """
        return AwsRunner(work_dir)
