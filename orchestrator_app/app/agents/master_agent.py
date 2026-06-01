import logging

from ..clients.watchtower_adapter import run_security_gate
from ..graph.state import EligibilityState


_LOGGER = logging.getLogger(__name__)


def run_master_agent(state: EligibilityState) -> EligibilityState:
    """
    Authorize the user query through the bilvantis_watchtower security gate.
    """
    result = run_security_gate(state)

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
