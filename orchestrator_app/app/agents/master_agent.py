from sqlalchemy.orm import Session

from ..clients.llm_client import LLMGenerationError, generate_llm_response, is_llm_configured
from ..graph.state import EligibilityState
from .prize_money_agent import run_prize_money_agent
from .response_agent import run_response_agent
from .savings_agent import run_savings_agent


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


def _classify_intent_with_llm(query: str) -> str | None:
    if not is_llm_configured():
        return None

    prompt = (
        "Classify the user query into exactly one label and return only the label.\n"
        "Allowed labels: lottery_eligibility, bank_balance, bank_tenure, unsupported.\n"
        f"User query: {query!r}"
    )
    try:
        raw = generate_llm_response(prompt)
    except LLMGenerationError:
        return None

    if not raw:
        return None

    normalized = raw.strip().lower()
    if normalized in {
        "lottery_eligibility",
        "bank_balance",
        "bank_tenure",
        "unsupported",
    }:
        return normalized
    return None


def _classify_intent_with_rules(normalized_query: str) -> str:
    balance_terms = ("balance", "savings", "account amount", "how much money")
    tenure_terms = ("years", "tenure", "how long", "with the bank")
    lottery_terms = ("lottery", "eligible", "eligibility", "qualify", "qualified")

    if _contains_any(normalized_query, lottery_terms):
        return "lottery_eligibility"
    if _contains_any(normalized_query, balance_terms):
        return "bank_balance"
    if _contains_any(normalized_query, tenure_terms):
        return "bank_tenure"
    return "unsupported"


def run_master_agent(state: EligibilityState) -> EligibilityState:
    """
    Classify the user query and apply lightweight input guardrails.
    Uses LLM-first intent routing with deterministic fallback rules.
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

    llm_intent = _classify_intent_with_llm(query)
    state["normalized_intent"] = llm_intent or _classify_intent_with_rules(normalized_query)
    if state["normalized_intent"] == "unsupported":
        state["decision_reason"] = "unsupported_query"

    state["guardrail_status"] = (
        "allowed" if state["normalized_intent"] != "unsupported" else "blocked"
    )
    return state


def run_master_orchestration(state: EligibilityState, db: Session) -> EligibilityState:
    """
    End-to-end Phase 5 master orchestration.

    Flow:
    1. Classify intent and apply guardrails.
    2. If blocked, generate response immediately.
    3. Fetch savings data.
    4. Run eligibility decision for lottery intent.
    5. Generate final response.
    """
    state = run_master_agent(state)

    if state.get("guardrail_status") == "blocked":
        return run_response_agent(state)

    state = run_savings_agent(state, db)
    if state.get("decision_reason") == "user_not_found":
        return state

    if state.get("normalized_intent") == "lottery_eligibility":
        state = run_prize_money_agent(state)
    else:
        state["decision_reason"] = "savings_data_answered_requested_intent"

    return run_response_agent(state)
