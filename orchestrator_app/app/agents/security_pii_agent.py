import sys
from pathlib import Path

from ..clients.llm_client import LLMGenerationError, generate_llm_response
from ..graph.state import EligibilityState


_SDK_SRC = Path(__file__).resolve().parents[3] / "bilvantis_watchtower" / "src"
if str(_SDK_SRC) not in sys.path:
    sys.path.insert(0, str(_SDK_SRC))

from bilvantis_watchtower.pipeline import run_security_and_pii
from bilvantis_watchtower.pii.ensemble import PIIDetectionError
from bilvantis_watchtower.exceptions import SecurityResponseError
from bilvantis_watchtower.types import SecurityPIIState


def run_security_pii_agent(state: EligibilityState) -> SecurityPIIState:
    try:
        return run_security_and_pii(state, generate_llm_response)
    except (SecurityResponseError, PIIDetectionError) as exc:
        raise LLMGenerationError(str(exc)) from exc
