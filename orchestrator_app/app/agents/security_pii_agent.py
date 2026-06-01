from ..clients.watchtower_adapter import run_security_and_pii
from ..graph.state import EligibilityState


def run_security_pii_agent(state: EligibilityState) -> EligibilityState:
    return run_security_and_pii(state)
