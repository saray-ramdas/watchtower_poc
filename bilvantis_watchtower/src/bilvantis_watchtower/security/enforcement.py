from bilvantis_watchtower.exceptions import SecurityResponseError
from bilvantis_watchtower.security.guardrails import (
    BLOCKED_TERMS,
    BULK_DATA_TERMS,
    classify_intent,
    classify_scope,
    contains_any,
    extract_mentioned_user_ids,
    normalize_query,
)
from bilvantis_watchtower.security.malicious_intent import (
    build_security_prompt,
    matches_required_security_response,
)
from bilvantis_watchtower.types import SecurityLLMGenerator, SecurityState


def run_security_gate(
    state: SecurityState,
    generate_llm_response: SecurityLLMGenerator,
) -> SecurityState:
    query = state.get("original_query", "")
    authenticated_user_id = state.get("user_id", "")
    normalized_query = normalize_query(query)

    state["mentioned_user_ids"] = extract_mentioned_user_ids(query)

    if not normalized_query.strip():
        state["normalized_intent"] = "unsupported"
        _set_blocked(state, "empty_query", "unsupported", "general_false")
        state["security_response"] = generate_security_llm_response(
            state,
            generate_llm_response,
        )
        return state

    state["normalized_intent"] = classify_intent(normalized_query)

    if state["normalized_intent"] == "unsupported" and not contains_any(
        normalized_query,
        BLOCKED_TERMS + BULK_DATA_TERMS,
    ):
        _set_blocked(state, "unsupported_query", "unsupported", "general_false")
        state["security_response"] = generate_security_llm_response(
            state,
            generate_llm_response,
        )
        return state

    requested_scope = classify_scope(
        normalized_query,
        authenticated_user_id,
        state["mentioned_user_ids"],
    )
    state["requested_scope"] = requested_scope

    if contains_any(normalized_query, BLOCKED_TERMS):
        _set_blocked(state, "query_failed_guardrails", requested_scope, "malicious")
    elif requested_scope == "all_users":
        _set_blocked(state, "all_users_denied", requested_scope, "malicious")
    elif requested_scope == "other_user":
        _set_blocked(state, "other_user_data_denied", requested_scope, "malicious")
    elif requested_scope == "unknown":
        _set_blocked(
            state,
            "ambiguous_user_context_denied",
            requested_scope,
            "general_false",
        )
    elif state["normalized_intent"] == "unsupported":
        _set_blocked(state, "unsupported_query", "unsupported", "general_false")
    else:
        _set_allowed(state)

    state["security_response"] = generate_security_llm_response(
        state,
        generate_llm_response,
    )
    return state


def generate_security_llm_response(
    state: SecurityState,
    generate_llm_response: SecurityLLMGenerator,
) -> str:
    prompt = build_security_prompt(state)
    generated = generate_llm_response(prompt)

    if generated is None:
        raise SecurityResponseError("LLM generator is required for security responses")

    expected_decision = state.get("security_decision", "no")
    risk_type = state.get("security_risk_type", "general_false")
    if matches_required_security_response(generated, expected_decision, risk_type):
        return generated.strip()

    retry_prompt = (
        f"{prompt}\n\n"
        "Your previous response did not match the required format. "
        f"Return exactly two lines. First line: {expected_decision}. "
        "Second line must start with Warning: for malicious prompts, otherwise Reason:."
    )
    regenerated = generate_llm_response(retry_prompt)
    if regenerated and matches_required_security_response(
        regenerated,
        expected_decision,
        risk_type,
    ):
        return regenerated.strip()

    raise SecurityResponseError("Security LLM response failed guardrails")


def _set_blocked(
    state: SecurityState,
    reason: str,
    requested_scope: str,
    risk_type: str,
) -> SecurityState:
    state["security_decision"] = "no"
    state["security_reason"] = reason
    state["security_risk_type"] = risk_type
    state["requested_scope"] = requested_scope
    state["guardrail_status"] = "blocked"
    state["decision_reason"] = reason
    return state


def _set_allowed(state: SecurityState) -> SecurityState:
    state["security_decision"] = "yes"
    state["security_reason"] = "self_query_allowed"
    state["security_risk_type"] = "allowed"
    state["requested_scope"] = "self"
    state["guardrail_status"] = "allowed"
    state["decision_reason"] = "self_query_allowed"
    return state
