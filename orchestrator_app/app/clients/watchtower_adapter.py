from bilvantis_watchtower import SecurityPIIState, SecurityState, Watchtower, WatchtowerError

from .llm_client import LLMGenerationError, generate_llm_response


_watchtower = Watchtower(generate_llm_response)


def run_security_gate(state: SecurityState) -> SecurityState:
    try:
        return _watchtower.run_security_gate(state)
    except WatchtowerError as exc:
        raise LLMGenerationError(str(exc)) from exc


def run_security_and_pii(state: SecurityPIIState) -> SecurityPIIState:
    try:
        return _watchtower.run_security_and_pii(state)
    except WatchtowerError as exc:
        raise LLMGenerationError(str(exc)) from exc
