"""AI agents for the wetwire-agent workflow.

This module provides:
- DeveloperAgent: Simulates a developer with a specific persona
- RunnerAgent: AI agent with access to wetwire CLI tools
- AIConversationHandler: Orchestrates Developer <-> Runner conversation
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import anthropic

from wetwire_agent.runner import Message


# System prompts
DEVELOPER_SYSTEM_PROMPT = """You are a developer who wants to create AWS infrastructure using wetwire.
You are having a conversation with a Runner agent who will help create the infrastructure.

{persona_instructions}

IMPORTANT RULES:
- Stay in character as the developer with the given persona
- Answer questions about your requirements
- You do NOT have access to any tools - only the Runner does
- When the Runner says they are done, respond with exactly: "DONE"
- Keep responses concise (1-3 sentences typically)
"""

RUNNER_SYSTEM_PROMPT = """You are a Runner agent that creates AWS infrastructure using wetwire-aws.

Your job: Take the user's infrastructure request and GENERATE THE CODE for it.

## NEW PACKAGE WORKFLOW

When starting fresh:
1. init_package - Create the package with a descriptive name
2. write_file - Write the COMPLETE infrastructure code to resources.py
3. run_lint - Check for issues (call immediately after write_file)
4. If lint fails: fix and write_file + run_lint again
5. run_build - Generate CloudFormation template
6. Tell user what you created

IMPORTANT: After init_package, you MUST immediately write_file with the actual infrastructure code.

## EXISTING PACKAGE WORKFLOW

When the message starts with [EXISTING PACKAGE: name]:
1. read_file - Read existing files to understand current state
2. write_file - Add or modify resources as requested
3. run_lint - Check for issues (call immediately after write_file)
4. If lint fails: fix and write_file + run_lint again
5. run_build - Generate CloudFormation template
6. Tell user what you changed

Do NOT call init_package for existing packages - just read and write files directly.

## FILE ORGANIZATION

Split resources into logical files:
- network.py - VPC, Subnets, Security Groups, Internet Gateways
- compute.py - EC2 instances, Lambda functions, ECS
- storage.py - S3 buckets, EBS volumes, RDS, DynamoDB
- security.py - IAM roles, policies, KMS keys

## TOOL RULES

- After EVERY write_file, call run_lint in the SAME response
- NEVER say "completed" without lint passing first
- When you see STOP/ERROR, call run_lint immediately

## MODULE PATH PATTERNS

- Resources: s3.Bucket, ec2.Instance, lambda_.Function
- PropertyTypes: s3.bucket.ServerSideEncryptionByDefault, s3.bucket.PublicAccessBlockConfiguration
- Enums: s3.ServerSideEncryption.AES256, lambda_.Runtime.PYTHON3_12

## CODE EXAMPLE

```python
from . import *

class MyEncryptionDefault:
    resource: s3.bucket.ServerSideEncryptionByDefault
    sse_algorithm = s3.ServerSideEncryption.AES256

class MyEncryptionRule:
    resource: s3.bucket.ServerSideEncryptionRule
    server_side_encryption_by_default = MyEncryptionDefault

class MyEncryption:
    resource: s3.bucket.BucketEncryption
    server_side_encryption_configuration = [MyEncryptionRule]

class MyPublicAccessBlock:
    resource: s3.bucket.PublicAccessBlockConfiguration
    block_public_acls = True
    block_public_policy = True
    ignore_public_acls = True
    restrict_public_buckets = True

class MyBucket:
    resource: s3.Bucket
    bucket_encryption = MyEncryption
    public_access_block_configuration = MyPublicAccessBlock
```

## RULES

- Keep responses brief
- Make safe defaults (encryption, private access)
- NEVER say "completed" without lint passing first
- When you see STOP/ERROR, call run_lint immediately
"""


@dataclass
class ToolResult:
    """Result of a tool execution."""

    tool_use_id: str
    content: str
    is_error: bool = False
    tool_name: str = ""  # Track which tool was called


@dataclass
class DeveloperAgent:
    """AI agent that simulates a developer with a specific persona."""

    persona_name: str
    persona_instructions: str
    client: anthropic.Anthropic = field(default_factory=anthropic.Anthropic)
    model: str = "claude-sonnet-4-20250514"
    conversation: list[dict[str, Any]] = field(default_factory=list)

    def get_system_prompt(self) -> str:
        return DEVELOPER_SYSTEM_PROMPT.format(persona_instructions=self.persona_instructions)

    def respond(self, runner_message: str) -> str:
        """Get the Developer's response to a Runner message."""
        self.conversation.append({"role": "user", "content": runner_message})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            system=self.get_system_prompt(),
            messages=self.conversation,
        )

        assistant_message = response.content[0].text
        self.conversation.append({"role": "assistant", "content": assistant_message})

        return assistant_message


@dataclass
class RunnerAgent:
    """AI agent that creates infrastructure using wetwire tools."""

    output_dir: Path
    existing_package: str | None = None
    client: anthropic.Anthropic = field(default_factory=anthropic.Anthropic)
    model: str = "claude-sonnet-4-20250514"
    conversation: list[dict[str, Any]] = field(default_factory=list)
    package_name: str = ""

    def __post_init__(self):
        # If there's an existing package, set it as the current package
        if self.existing_package:
            self.package_name = self.existing_package
            # For existing packages, output_dir IS the package dir
            self._package_dir = self.output_dir
        else:
            self._package_dir = None

    @property
    def package_dir(self) -> Path | None:
        """Get the package directory."""
        if self._package_dir:
            return self._package_dir
        if self.package_name:
            return self.output_dir / self.package_name
        return None

    def get_tools(self) -> list[dict[str, Any]]:
        """Define the tools available to the Runner."""
        return [
            {
                "name": "init_package",
                "description": "Initialize a new wetwire-aws package. Creates __init__.py with setup_resources().",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "package_name": {
                            "type": "string",
                            "description": "Name for the package (snake_case, e.g., 'log_bucket')",
                        },
                        "description": {
                            "type": "string",
                            "description": "Brief description of what this package creates",
                        },
                    },
                    "required": ["package_name", "description"],
                },
            },
            {
                "name": "write_file",
                "description": "Write a Python file to the package. Use for resource definitions.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Filename (e.g., 'storage.py', 'compute.py')",
                        },
                        "content": {
                            "type": "string",
                            "description": "Python code content",
                        },
                    },
                    "required": ["filename", "content"],
                },
            },
            {
                "name": "run_lint",
                "description": "Run wetwire-aws lint on the package to check for issues.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "run_build",
                "description": "Run wetwire-aws build to generate CloudFormation template.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "read_file",
                "description": "Read a file from the package to see its current contents.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Filename to read (e.g., 'resources.py', 'network.py')",
                        },
                    },
                    "required": ["filename"],
                },
            },
            {
                "name": "ask_developer",
                "description": "Ask the developer a clarifying question. Use sparingly.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The question to ask the developer",
                        },
                    },
                    "required": ["question"],
                },
            },
        ]

    def execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> ToolResult:
        """Execute a tool and return the result."""
        tool_use_id = f"tool_{tool_name}"

        if tool_name == "init_package":
            result = self._init_package(tool_use_id, tool_input)
        elif tool_name == "write_file":
            result = self._write_file(tool_use_id, tool_input)
        elif tool_name == "read_file":
            result = self._read_file(tool_use_id, tool_input)
        elif tool_name == "run_lint":
            result = self._run_lint(tool_use_id)
        elif tool_name == "run_build":
            result = self._run_build(tool_use_id)
        elif tool_name == "ask_developer":
            # This is handled specially by the orchestrator
            result = ToolResult(
                tool_use_id=tool_use_id,
                content=f"QUESTION: {tool_input['question']}",
            )
        else:
            result = ToolResult(
                tool_use_id=tool_use_id,
                content=f"Unknown tool: {tool_name}",
                is_error=True,
            )

        # Always set the tool_name so orchestrator can track which tools were called
        result.tool_name = tool_name
        return result

    def _init_package(self, tool_use_id: str, tool_input: dict[str, Any]) -> ToolResult:
        """Initialize a new package using wetwire-aws init."""
        self.package_name = tool_input["package_name"]
        description = tool_input.get("description", f"{self.package_name} infrastructure")

        # Use wetwire-aws init CLI command
        result = subprocess.run(
            [
                sys.executable, "-m", "wetwire_aws.cli",
                "init", self.package_name,
                "-o", str(self.output_dir),
                "-d", description,
                "--force",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"Created package '{self.package_name}' at {self.output_dir / self.package_name}",
            )
        else:
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"Failed to create package: {result.stderr}",
                is_error=True,
            )

    def _write_file(self, tool_use_id: str, tool_input: dict[str, Any]) -> ToolResult:
        """Write a file to the package."""
        if not self.package_dir:
            return ToolResult(
                tool_use_id=tool_use_id,
                content="Error: Must init_package first",
                is_error=True,
            )

        file_path = self.package_dir / tool_input["filename"]
        file_path.write_text(tool_input["content"])

        return ToolResult(
            tool_use_id=tool_use_id,
            content=f"Wrote {tool_input['filename']} ({len(tool_input['content'])} bytes)",
        )

    def _read_file(self, tool_use_id: str, tool_input: dict[str, Any]) -> ToolResult:
        """Read a file from the package."""
        if not self.package_dir:
            return ToolResult(
                tool_use_id=tool_use_id,
                content="Error: No package initialized",
                is_error=True,
            )

        file_path = self.package_dir / tool_input["filename"]

        if not file_path.exists():
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"File not found: {tool_input['filename']}",
                is_error=True,
            )

        content = file_path.read_text()
        return ToolResult(
            tool_use_id=tool_use_id,
            content=f"Contents of {tool_input['filename']}:\n\n{content}",
        )

    def _run_lint(self, tool_use_id: str) -> ToolResult:
        """Run lint on the package."""
        if not self.package_dir:
            return ToolResult(
                tool_use_id=tool_use_id,
                content="Error: Must init_package first",
                is_error=True,
            )

        # Run lint without --fix so AI sees unfixable issues
        # AI will fix based on error messages
        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "lint", str(self.package_dir)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return ToolResult(
                tool_use_id=tool_use_id,
                content="Lint passed with no issues",
            )
        else:
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"Lint found issues:\n{result.stdout}\n{result.stderr}",
            )

    def _run_build(self, tool_use_id: str) -> ToolResult:
        """Run build on the package."""
        if not self.package_dir:
            return ToolResult(
                tool_use_id=tool_use_id,
                content="Error: Must init_package first",
                is_error=True,
            )

        # For existing packages, PYTHONPATH is parent of package_dir
        # For new packages, it's output_dir
        if self.existing_package:
            pythonpath = str(self.package_dir.parent)
        else:
            pythonpath = str(self.output_dir)

        result = subprocess.run(
            [sys.executable, "-m", "wetwire_aws.cli", "build", "-m", self.package_name, "-f", "yaml"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": pythonpath},
        )

        if result.returncode == 0:
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"Build successful. CloudFormation template:\n{result.stdout}",
            )
        else:
            return ToolResult(
                tool_use_id=tool_use_id,
                content=f"Build failed:\n{result.stderr}",
                is_error=True,
            )

    def run_turn(self, developer_message: str | None = None) -> tuple[str, list[ToolResult]]:
        """Run one turn of the Runner agent.

        Returns:
            Tuple of (response_text, tool_results)
        """
        if developer_message:
            self.conversation.append({"role": "user", "content": developer_message})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=RUNNER_SYSTEM_PROMPT,
            tools=self.get_tools(),
            messages=self.conversation,
        )

        # Process response
        tool_results: list[ToolResult] = []
        response_text = ""

        for block in response.content:
            if block.type == "text":
                response_text += block.text
            elif block.type == "tool_use":
                result = self.execute_tool(block.name, block.input)
                result.tool_use_id = block.id
                tool_results.append(result)

        # Add assistant message to conversation
        self.conversation.append({"role": "assistant", "content": response.content})

        # If there were tool uses, add tool results and continue
        if tool_results:
            tool_result_content = [
                {
                    "type": "tool_result",
                    "tool_use_id": r.tool_use_id,
                    "content": r.content,
                    "is_error": r.is_error,
                }
                for r in tool_results
            ]
            self.conversation.append({"role": "user", "content": tool_result_content})

        return response_text, tool_results

    def run_turn_streaming(
        self,
        developer_message: str | None = None,
        on_text: callable = None,
        on_tool_start: callable = None,
        on_tool_end: callable = None,
    ) -> tuple[str, list[ToolResult]]:
        """Run one turn with streaming output.

        Args:
            developer_message: Message from the developer
            on_text: Callback for text chunks: on_text(chunk: str)
            on_tool_start: Callback when tool starts: on_tool_start(name: str, input: dict)
            on_tool_end: Callback when tool ends: on_tool_end(name: str, result: ToolResult)

        Returns:
            Tuple of (response_text, tool_results)
        """
        if developer_message:
            self.conversation.append({"role": "user", "content": developer_message})

        tool_results: list[ToolResult] = []
        response_text = ""
        current_tool_name = None
        current_tool_input = {}

        with self.client.messages.stream(
            model=self.model,
            max_tokens=4096,
            system=RUNNER_SYSTEM_PROMPT,
            tools=self.get_tools(),
            messages=self.conversation,
        ) as stream:
            for event in stream:
                if event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        current_tool_name = event.content_block.name
                        current_tool_input = {}
                        if on_tool_start:
                            on_tool_start(current_tool_name, {})

                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        chunk = event.delta.text
                        response_text += chunk
                        if on_text:
                            on_text(chunk)
                    elif event.delta.type == "input_json_delta":
                        # Accumulate tool input JSON
                        pass  # We'll get the full input from the final message

                elif event.type == "content_block_stop":
                    if current_tool_name:
                        # Tool block finished - execute it
                        current_tool_name = None

            # Get the final message to extract tool uses
            final_message = stream.get_final_message()

        # Process the final message for tool uses
        for block in final_message.content:
            if block.type == "tool_use":
                result = self.execute_tool(block.name, block.input)
                result.tool_use_id = block.id
                tool_results.append(result)
                if on_tool_end:
                    on_tool_end(block.name, result)

        # Add assistant message to conversation
        self.conversation.append({"role": "assistant", "content": final_message.content})

        # If there were tool uses, add tool results
        if tool_results:
            tool_result_content = [
                {
                    "type": "tool_result",
                    "tool_use_id": r.tool_use_id,
                    "content": r.content,
                    "is_error": r.is_error,
                }
                for r in tool_results
            ]
            self.conversation.append({"role": "user", "content": tool_result_content})

        return response_text, tool_results


@dataclass
class AIConversationHandler:
    """Orchestrates Developer <-> Runner conversation."""

    prompt: str
    persona_name: str
    persona_instructions: str
    output_dir: Path
    max_turns: int = 10
    messages: list[Message] = field(default_factory=list)

    def run(self) -> tuple[Path | None, list[Message]]:
        """Run the full conversation.

        Returns:
            Tuple of (package_path or None, conversation messages)
        """
        developer = DeveloperAgent(
            persona_name=self.persona_name,
            persona_instructions=self.persona_instructions,
        )
        runner = RunnerAgent(output_dir=self.output_dir)

        # Start with the developer's prompt
        self.messages.append(Message(role="developer", content=self.prompt))
        current_message = self.prompt

        # Track tool usage - more aggressive enforcement
        lint_called = False
        lint_passed = False
        build_called = False
        pending_lint = False  # True when write_file called but lint not yet run

        for turn in range(self.max_turns):
            # Runner's turn
            response_text, tool_results = runner.run_turn(current_message)

            # Track which tools were called this turn
            wrote_file_this_turn = False
            ran_lint_this_turn = False

            for result in tool_results:
                if result.tool_name == "run_lint":
                    lint_called = True
                    ran_lint_this_turn = True
                    pending_lint = False  # Lint was run, no longer pending
                    lint_passed = "passed" in result.content.lower() or "no issues" in result.content.lower()
                    # Add lint result to conversation for visibility
                    status = "PASS" if lint_passed else "FAIL"
                    self.messages.append(
                        Message(role="tool", content=f"[lint {status}] {result.content}")
                    )
                elif result.tool_name == "run_build":
                    build_called = True
                    # Add build result to conversation for visibility
                    build_ok = not result.is_error
                    status = "OK" if build_ok else "FAIL"
                    self.messages.append(
                        Message(role="tool", content=f"[build {status}] {result.content[:200]}...")
                    )
                elif result.tool_name == "write_file":
                    wrote_file_this_turn = True
                    pending_lint = True  # Need to lint after writing
                    lint_passed = False  # Reset - code changed

            # ENFORCEMENT: If wrote file but didn't lint in same turn, force lint
            if wrote_file_this_turn and not ran_lint_this_turn:
                current_message = (
                    "STOP: You wrote a file but did not call run_lint. "
                    "You MUST call run_lint immediately after writing code. "
                    "Call run_lint now before doing anything else."
                )
                self.messages.append(Message(role="system", content=current_message))
                continue

            # ENFORCEMENT: If runner talks about "fixing" without running lint, force lint
            fix_keywords = ["let me fix", "i'll fix", "fixing", "i need to fix", "let me correct"]
            if response_text and any(kw in response_text.lower() for kw in fix_keywords):
                if pending_lint or not lint_called:
                    current_message = (
                        "STOP: You mentioned fixing but did not run the linter first. "
                        "You MUST call run_lint to see actual errors before attempting fixes. "
                        "Call run_lint now."
                    )
                    self.messages.append(Message(role="system", content=current_message))
                    continue

            # Check for questions to developer
            question = None
            for result in tool_results:
                if result.content.startswith("QUESTION:"):
                    question = result.content[9:].strip()
                    break

            if question:
                # Ask the developer
                self.messages.append(Message(role="runner", content=question))
                developer_response = developer.respond(question)
                self.messages.append(Message(role="developer", content=developer_response))

                if "DONE" in developer_response.upper():
                    break

                current_message = developer_response
            else:
                # No question - check if runner is done
                if response_text:
                    self.messages.append(Message(role="runner", content=response_text))

                if "completed" in response_text.lower() or "done" in response_text.lower():
                    # Validate that lint was called before accepting completion
                    if not lint_called or pending_lint:
                        current_message = (
                            "ERROR: You must call run_lint before saying you're done. "
                            "Please run the linter now."
                        )
                        self.messages.append(Message(role="system", content=current_message))
                        continue
                    elif not lint_passed:
                        current_message = (
                            "ERROR: Lint did not pass. "
                            "Please fix the issues and run lint again."
                        )
                        self.messages.append(Message(role="system", content=current_message))
                        continue
                    break

                # Continue with tool results feedback
                current_message = None

            # Safety check - if no package created after several turns, something's wrong
            if turn > 5 and not runner.package_name:
                self.messages.append(
                    Message(role="system", content="Warning: No package created after multiple turns")
                )
                break

        # Only return the package path if the workflow completed properly
        # (lint must have been called and passed)
        package_path = None
        if runner.package_name and lint_called and lint_passed:
            package_path = self.output_dir / runner.package_name
        elif runner.package_name:
            # Package was created but workflow didn't complete properly
            self.messages.append(
                Message(
                    role="system",
                    content=f"FAILED: Package created but lint was not run or did not pass. "
                    f"lint_called={lint_called}, lint_passed={lint_passed}",
                )
            )

        return package_path, self.messages


def run_ai_scenario(
    prompt: str,
    persona_name: str,
    persona_instructions: str,
    output_dir: Path | None = None,
) -> tuple[Path | None, list[Message]]:
    """Run a scenario with AI agents.

    Args:
        prompt: The developer's initial prompt
        persona_name: Name of the persona
        persona_instructions: Instructions for the developer persona
        output_dir: Directory to create the package in

    Returns:
        Tuple of (package_path or None, conversation messages)
    """
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="wetwire-ai-"))

    handler = AIConversationHandler(
        prompt=prompt,
        persona_name=persona_name,
        persona_instructions=persona_instructions,
        output_dir=output_dir,
    )

    return handler.run()


@dataclass
class InteractiveConversationHandler:
    """Orchestrates Human Developer <-> AI Runner conversation with streaming output."""

    output_dir: Path
    existing_package: str | None = None
    existing_files: list[str] = field(default_factory=list)
    max_turns: int = 20

    def run(self, initial_prompt: str) -> tuple[Path | None, list[Message]]:
        """Run an interactive design session.

        Args:
            initial_prompt: The developer's initial prompt

        Returns:
            Tuple of (package_path or None, conversation messages)
        """
        runner = RunnerAgent(
            output_dir=self.output_dir,
            existing_package=self.existing_package,
        )
        messages: list[Message] = []

        # Track tool usage
        lint_called = False
        lint_passed = False
        build_succeeded = False

        # If existing package, prefix the prompt with context
        if self.existing_package:
            context = f"[EXISTING PACKAGE: {self.existing_package}]\n"
            context += f"[FILES: {', '.join(self.existing_files) if self.existing_files else 'none'}]\n\n"
            current_message = context + initial_prompt
        else:
            current_message = initial_prompt

        messages.append(Message(role="developer", content=initial_prompt))

        # Callbacks for streaming output
        def on_text(chunk: str) -> None:
            print(chunk, end="", flush=True)

        def on_tool_start(name: str, input: dict) -> None:
            print(f"\n\033[90m[{name}] Running...\033[0m", flush=True)

        def on_tool_end(name: str, result: ToolResult) -> None:
            nonlocal lint_called, lint_passed, build_succeeded
            if name == "run_lint":
                lint_called = True
                lint_passed = "passed" in result.content.lower() or "no issues" in result.content.lower()
                status = "\033[32mPASS\033[0m" if lint_passed else "\033[31mFAIL\033[0m"
                print(f"\033[90m[{name}] {status}: {result.content}\033[0m", flush=True)
            elif name == "run_build":
                build_succeeded = not result.is_error
                status = "\033[32mOK\033[0m" if build_succeeded else "\033[31mFAIL\033[0m"
                # Truncate build output
                content = result.content[:300] + "..." if len(result.content) > 300 else result.content
                print(f"\033[90m[{name}] {status}: {content}\033[0m", flush=True)
            elif name == "init_package":
                print(f"\033[90m[{name}] {result.content}\033[0m", flush=True)
            elif name == "write_file":
                print(f"\033[90m[{name}] {result.content}\033[0m", flush=True)
            elif name == "read_file":
                # Truncate file content display
                content = result.content[:200] + "..." if len(result.content) > 200 else result.content
                print(f"\033[90m[{name}] {content}\033[0m", flush=True)

        print("\n\033[1mRunner:\033[0m ", end="", flush=True)

        for turn in range(self.max_turns):
            # Runner's turn with streaming
            response_text, tool_results = runner.run_turn_streaming(
                current_message,
                on_text=on_text,
                on_tool_start=on_tool_start,
                on_tool_end=on_tool_end,
            )

            if response_text:
                messages.append(Message(role="runner", content=response_text))

            # Check for questions to developer
            question = None
            for result in tool_results:
                if result.content.startswith("QUESTION:"):
                    question = result.content[9:].strip()
                    break

            if question:
                # Ask the human developer
                print(f"\n\n\033[1mRunner asks:\033[0m {question}")
                print("\033[1mType something:\033[0m ", end="")
                developer_response = input()

                if developer_response.lower() in ("quit", "exit", "q"):
                    print("\n\033[33mSession ended by user.\033[0m")
                    break

                messages.append(Message(role="developer", content=developer_response))
                current_message = developer_response
                print("\n\033[1mRunner:\033[0m ", end="", flush=True)
            else:
                # Check if build just succeeded - that's our completion signal
                just_built = any(
                    getattr(r, 'tool_name', '') == 'run_build' and not r.is_error
                    for r in tool_results
                )

                if just_built and build_succeeded:
                    # Task completed successfully - ask what's next
                    print("\n\n\033[1mWhat's next?\033[0m  ( type done to exit ): ", end="")
                    developer_response = input()

                    if developer_response.lower() in ("quit", "exit", "q", "done", ""):
                        print("\n\033[33mSession ended.\033[0m")
                        break

                    messages.append(Message(role="developer", content=developer_response))
                    current_message = developer_response
                    print("\n\033[1mRunner:\033[0m ", end="", flush=True)

                elif tool_results:
                    # Tools were executed but not done yet - let AI continue
                    current_message = None
                    print("\n\033[1mRunner:\033[0m ", end="", flush=True)

                else:
                    # AI output text without tools - needs user input
                    print("\n\n\033[1mType something:\033[0m ", end="")
                    developer_response = input()

                    if developer_response.lower() in ("quit", "exit", "q", "done", ""):
                        print("\n\033[33mSession ended.\033[0m")
                        break

                    messages.append(Message(role="developer", content=developer_response))
                    current_message = developer_response
                    print("\n\033[1mRunner:\033[0m ", end="", flush=True)

        # Return the package path if created and build succeeded
        package_path = None
        if runner.package_dir and build_succeeded:
            package_path = runner.package_dir

        return package_path, messages


def detect_existing_package(directory: Path) -> tuple[str | None, list[str]]:
    """Detect if directory contains an existing wetwire-aws package.

    Returns:
        Tuple of (package_name or None, list of .py files)
    """
    init_file = directory / "__init__.py"
    if not init_file.exists():
        return None, []

    content = init_file.read_text()
    if "setup_resources" not in content:
        return None, []

    # Found a package - get its name and files
    package_name = directory.name
    py_files = [f.name for f in directory.glob("*.py") if f.name != "__init__.py"]

    return package_name, py_files


def run_interactive_design(
    initial_prompt: str | None = None,
    output_dir: Path | None = None,
) -> tuple[Path | None, list[Message]]:
    """Run an interactive design session.

    Args:
        initial_prompt: Optional initial prompt (will prompt if not provided)
        output_dir: Directory to create the package in

    Returns:
        Tuple of (package_path or None, conversation messages)
    """
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="wetwire-design-"))

    # Check for existing package in output_dir
    existing_package, existing_files = detect_existing_package(output_dir)

    if existing_package:
        print(f"\033[33mFound existing package: {existing_package}\033[0m")
        print(f"\033[90mFiles: {', '.join(existing_files) if existing_files else '(none)'}\033[0m")
        print()

    handler = InteractiveConversationHandler(
        output_dir=output_dir,
        existing_package=existing_package,
        existing_files=existing_files,
    )

    if initial_prompt is None:
        if existing_package:
            print("\033[1mWhat would you like to add or change?\033[0m")
        else:
            print("\033[1mDescribe what infrastructure you need:\033[0m")
        print("\033[1mType something:\033[0m ", end="")
        initial_prompt = input()

    return handler.run(initial_prompt)
