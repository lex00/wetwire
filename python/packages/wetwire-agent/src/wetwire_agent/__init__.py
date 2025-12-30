"""wetwire-agent: Testing and design orchestration for wetwire domain packages."""

__version__ = "0.1.0"

from wetwire_agent.core.orchestrator import Orchestrator
from wetwire_agent.core.personas import Persona, load_persona
from wetwire_agent.core.scoring import Score, calculate_score
from wetwire_agent.core.results import ResultsWriter

__all__ = [
    "Orchestrator",
    "Persona",
    "load_persona",
    "Score",
    "calculate_score",
    "ResultsWriter",
]
