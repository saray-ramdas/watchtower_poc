from bilvantis_watchtower.pii.ensemble import detect_pii_entities
from bilvantis_watchtower.pii.redactor import redact_query_with_tokens
from bilvantis_watchtower.security.enforcement import run_security_gate
from bilvantis_watchtower.types import SecurityLLMGenerator, SecurityPIIState


def run_security_and_pii(
    state: SecurityPIIState,
    generate_llm_response: SecurityLLMGenerator,
) -> SecurityPIIState:
    secured_state = run_security_gate(state, generate_llm_response)
    query = secured_state.get("original_query", "")

    pii_entities = detect_pii_entities(query, generate_llm_response)
    masked_query, applied_entities = redact_query_with_tokens(query, pii_entities)
    secured_state["masked_query"] = masked_query
    secured_state["pii_entities"] = applied_entities
    return secured_state
