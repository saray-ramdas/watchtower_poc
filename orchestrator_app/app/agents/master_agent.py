from ..graph.state import EligibilityState


_BLOCKED_TERMS = (
    "ignore previous",
    "ignore instructions",
    "system prompt",
    "developer message",
    "drop table",
    "delete from",
    "password",
    "secret",
    "ssn",
    "social security",
)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def run_master_agent(state: EligibilityState) -> EligibilityState:
    """
    Classify the user query and apply lightweight input guardrails.
    """
    query = state.get("original_query", "")
    normalized_query = query.lower().strip()

    if not normalized_query:
        state["normalized_intent"] = "unsupported"
        state["guardrail_status"] = "blocked"
        state["decision_reason"] = "empty_query"
        return state

    if _contains_any(normalized_query, _BLOCKED_TERMS):
        state["normalized_intent"] = "unsupported"
        state["guardrail_status"] = "blocked"
        state["decision_reason"] = "query_failed_guardrails"
        return state

    balance_terms = ("balance", "savings", "account amount", "how much money")
    tenure_terms = ("years", "tenure", "how long", "with the bank")
    lottery_terms = ("lottery", "eligible", "eligibility", "qualify", "qualified")

    if _contains_any(normalized_query, lottery_terms):
        state["normalized_intent"] = "lottery_eligibility"
    elif _contains_any(normalized_query, balance_terms):
        state["normalized_intent"] = "bank_balance"
    elif _contains_any(normalized_query, tenure_terms):
        state["normalized_intent"] = "bank_tenure"
    else:
        state["normalized_intent"] = "unsupported"
        state["decision_reason"] = "unsupported_query"

    state["guardrail_status"] = (
        "allowed" if state["normalized_intent"] != "unsupported" else "blocked"
    )
    return state
