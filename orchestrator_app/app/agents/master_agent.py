import logging
import sys
from pathlib import Path

from ..clients.llm_client import LLMGenerationError, generate_llm_response
from ..graph.state import EligibilityState


_SDK_SRC = Path(__file__).resolve().parents[3] / "bilvantis_watchtower" / "src"
if str(_SDK_SRC) not in sys.path:
    sys.path.insert(0, str(_SDK_SRC))

from bilvantis_watchtower.exceptions import SecurityResponseError
from bilvantis_watchtower.security.enforcement import run_security_gate


_LOGGER = logging.getLogger(__name__)


def run_master_agent(state: EligibilityState) -> EligibilityState:
    """
    Authorize the user query through the bilvantis_watchtower security gate.
    """
    try:
        result = run_security_gate(state, generate_llm_response)
    except SecurityResponseError as exc:
        raise LLMGenerationError(str(exc)) from exc

    _LOGGER.info(
        "security_decision user_id=%s decision=%s scope=%s intent=%s risk=%s reason=%s",
        result.get("user_id"),
        result.get("security_decision"),
        result.get("requested_scope"),
        result.get("normalized_intent"),
        result.get("security_risk_type"),
        result.get("security_reason"),
    )
    return result
