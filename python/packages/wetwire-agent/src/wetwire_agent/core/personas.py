"""Persona loading and configuration.

Personas configure Developer behavior during testing. Each persona tests
different Runner capabilities:

- beginner: Vague requirements, defers to suggestions
- intermediate: Mixed clarity, asks clarifying questions
- expert: Precise requirements, corrects mistakes
- terse: Minimal responses ("yes", "no")
- verbose: Over-explains, adds tangents
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Persona:
    """Represents a testing persona.

    Attributes:
        name: Persona identifier (e.g., "beginner", "expert")
        description: Brief description of the persona's behavior
        system_prompt: System prompt for AI Developer configuration
        traits: List of behavioral traits
    """

    name: str
    description: str
    system_prompt: str
    traits: list[str]


# Built-in personas
BEGINNER = Persona(
    name="beginner",
    description="Vague requirements, defers to suggestions",
    system_prompt=(
        "You are a beginner user who is new to infrastructure. "
        "You have vague requirements and often defer to suggestions. "
        "You may not know the right terminology."
    ),
    traits=["vague", "deferential", "inexperienced"],
)

INTERMEDIATE = Persona(
    name="intermediate",
    description="Mixed clarity, asks clarifying questions",
    system_prompt=(
        "You are an intermediate user with some infrastructure experience. "
        "You have generally clear requirements but may need to clarify some details. "
        "You ask clarifying questions when unsure."
    ),
    traits=["generally_clear", "inquisitive", "collaborative"],
)

EXPERT = Persona(
    name="expert",
    description="Precise requirements, corrects mistakes",
    system_prompt=(
        "You are an expert user with deep infrastructure knowledge. "
        "You have precise requirements and will correct the Runner's mistakes. "
        "You expect high-quality output and will push back on suboptimal solutions."
    ),
    traits=["precise", "demanding", "knowledgeable"],
)

TERSE = Persona(
    name="terse",
    description="Minimal responses",
    system_prompt=(
        "You are a terse user who gives minimal responses. "
        "You answer questions with 'yes', 'no', or very brief phrases. "
        "You don't elaborate unless absolutely necessary."
    ),
    traits=["minimal", "brief", "unelaborative"],
)

VERBOSE = Persona(
    name="verbose",
    description="Over-explains, adds tangents",
    system_prompt=(
        "You are a verbose user who over-explains everything. "
        "You add tangents and extra context that may not be relevant. "
        "The Runner must filter signal from noise."
    ),
    traits=["wordy", "tangential", "detailed"],
)

PERSONAS = {
    "beginner": BEGINNER,
    "intermediate": INTERMEDIATE,
    "expert": EXPERT,
    "terse": TERSE,
    "verbose": VERBOSE,
}


def load_persona(name: str) -> Persona:
    """Load a persona by name.

    Args:
        name: Persona name (beginner, intermediate, expert, terse, verbose)

    Returns:
        The requested Persona

    Raises:
        ValueError: If the persona name is not recognized
    """
    if name not in PERSONAS:
        valid = ", ".join(PERSONAS.keys())
        raise ValueError(f"Unknown persona '{name}'. Valid: {valid}")
    return PERSONAS[name]


def load_persona_from_file(path: Path) -> Persona:
    """Load a custom persona from a markdown file.

    The file should have YAML frontmatter with persona configuration.

    Args:
        path: Path to the persona markdown file

    Returns:
        A Persona loaded from the file

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file format is invalid
    """
    # TODO: Implement markdown/YAML parsing
    raise NotImplementedError("Custom persona loading not yet implemented")
