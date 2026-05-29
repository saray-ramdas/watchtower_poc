import logging
import re
from pathlib import Path

from ..clients.llm_client import LLMGenerationError, generate_llm_response
from ..graph.state import EligibilityState

try:
    from jinja2 import Template
except ImportError:
    Template = None


_PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"
_SECURITY_GUARDRAILS_PATH = _PROMPT_DIR / "security_guardrails.j2"
_SECURITY_DECISION_PROMPT_PATH = _PROMPT_DIR / "security_decision_prompt.j2"
_SECURITY_MALICIOUS_PROMPT_PATH = _PROMPT_DIR / "security_malicious_prompt.j2"
_LOGGER = logging.getLogger(__name__)

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
    "credential",
    "api key",
)

_BULK_DATA_TERMS = (
    "all users",
    "all user",
    "all customers",
    "all customer",
    "everyone",
    "every user",
    "every customer",
    "list of users",
    "list users",
    "customer list",
    "entire data",
    "entire database",
    "full database",
    "full customer",
    "all records",
    "show table",
    "dump",
    "export",
)

_SELF_TERMS = (
    " i ",
    " me ",
    " my ",
    " mine ",
    " myself ",
    " am i ",
    " do i ",
    " have i ",
)

_USER_ID_PATTERN = re.compile(r"\buser[\w-]*\b", re.IGNORECASE)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _normalize_query(query: str) -> str:
    return f" {query.lower().strip()} "


def _extract_mentioned_user_ids(query: str) -> list[str]:
    return sorted({match.group(0).lower() for match in _USER_ID_PATTERN.finditer(query)})


def _classify_intent(normalized_query: str) -> str:
    balance_terms = ("balance", "savings", "account amount", "how much money")
    tenure_terms = ("years", "tenure", "how long", "with the bank")
    lottery_terms = ("lottery", "eligible", "eligibility", "qualify", "qualified", "prize")

    if _contains_any(normalized_query, lottery_terms):
        return "lottery_eligibility"
    if _contains_any(normalized_query, balance_terms):
        return "bank_balance"
    if _contains_any(normalized_query, tenure_terms):
        return "bank_tenure"
    return "unsupported"


def _classify_scope(
    normalized_query: str,
    authenticated_user_id: str,
    mentioned_user_ids: list[str],
) -> str:
    normalized_user_id = authenticated_user_id.lower().strip()

    if _contains_any(normalized_query, _BULK_DATA_TERMS):
        return "all_users"

    if mentioned_user_ids:
        if all(user_id == normalized_user_id for user_id in mentioned_user_ids):
            return "self"
        return "other_user"

    third_person_terms = (
        " his ",
        " her ",
        " their ",
        " another user",
        " other user",
        " someone else",
        " other customer",
        " another customer",
    )
    if _contains_any(normalized_query, third_person_terms):
        return "unknown"

    if _contains_any(normalized_query, _SELF_TERMS):
        return "self"

    return "unknown"


def _set_blocked(
    state: EligibilityState,
    reason: str,
    requested_scope: str,
    risk_type: str,
) -> EligibilityState:
    state["security_decision"] = "no"
    state["security_reason"] = reason
    state["security_risk_type"] = risk_type
    state["requested_scope"] = requested_scope
    state["guardrail_status"] = "blocked"
    state["decision_reason"] = reason
    return state


def _set_allowed(state: EligibilityState) -> EligibilityState:
    state["security_decision"] = "yes"
    state["security_reason"] = "self_query_allowed"
    state["security_risk_type"] = "allowed"
    state["requested_scope"] = "self"
    state["guardrail_status"] = "allowed"
    state["decision_reason"] = "self_query_allowed"
    return state


def _render_template(template_path: Path, context: EligibilityState) -> str:
    if Template is None:
        raise LLMGenerationError("Jinja2 is required to render security prompts")
    if not template_path.exists():
        raise LLMGenerationError(f"Missing security prompt template: {template_path.name}")

    template = Template(template_path.read_text(encoding="utf-8"))
    return template.render(**context)


def _build_security_prompt(state: EligibilityState) -> str:
    guardrails = _render_template(_SECURITY_GUARDRAILS_PATH, state)
    decision_prompt = _render_template(_SECURITY_DECISION_PROMPT_PATH, state)
    malicious_prompt = _render_template(_SECURITY_MALICIOUS_PROMPT_PATH, state)
    return f"{guardrails}\n\n{decision_prompt}\n\n{malicious_prompt}"


def _matches_required_security_response(
    response: str,
    expected_decision: str,
    risk_type: str,
) -> bool:
    lines = [line.strip() for line in response.strip().splitlines() if line.strip()]
    if len(lines) != 2:
        return False

    expected_prefix = "warning:" if risk_type == "malicious" else "reason:"
    return lines[0].lower() == expected_decision and lines[1].lower().startswith(
        expected_prefix
    )


def generate_security_llm_response(state: EligibilityState) -> str:
    prompt = _build_security_prompt(state)
    generated = generate_llm_response(prompt)

    if generated is None:
        raise LLMGenerationError("Groq is required for security responses")

    expected_decision = state.get("security_decision", "no")
    risk_type = state.get("security_risk_type", "general_false")
    if _matches_required_security_response(generated, expected_decision, risk_type):
        return generated.strip()

    retry_prompt = (
        f"{prompt}\n\n"
        "Your previous response did not match the required format. "
        f"Return exactly two lines. First line: {expected_decision}. "
        "Second line must start with Warning: for malicious prompts, otherwise Reason:."
    )
    regenerated = generate_llm_response(retry_prompt)
    if regenerated and _matches_required_security_response(
        regenerated,
        expected_decision,
        risk_type,
    ):
        return regenerated.strip()

    raise LLMGenerationError("Security LLM response failed guardrails")


def run_master_agent(state: EligibilityState) -> EligibilityState:
    """
    Authorize the user query before any data-access or PII layer runs.
    """
    query = state.get("original_query", "")
    authenticated_user_id = state.get("user_id", "")
    normalized_query = _normalize_query(query)

    state["mentioned_user_ids"] = _extract_mentioned_user_ids(query)

    if not normalized_query.strip():
        state["normalized_intent"] = "unsupported"
        _set_blocked(state, "empty_query", "unsupported", "general_false")
        state["security_response"] = generate_security_llm_response(state)
        return state

    state["normalized_intent"] = _classify_intent(normalized_query)

    if state["normalized_intent"] == "unsupported" and not _contains_any(
        normalized_query,
        _BLOCKED_TERMS + _BULK_DATA_TERMS,
    ):
        _set_blocked(state, "unsupported_query", "unsupported", "general_false")
        state["security_response"] = generate_security_llm_response(state)
        return state

    requested_scope = _classify_scope(
        normalized_query,
        authenticated_user_id,
        state["mentioned_user_ids"],
    )
    state["requested_scope"] = requested_scope

    if _contains_any(normalized_query, _BLOCKED_TERMS):
        _set_blocked(state, "query_failed_guardrails", requested_scope, "malicious")
    elif requested_scope == "all_users":
        _set_blocked(state, "all_users_denied", requested_scope, "malicious")
    elif requested_scope == "other_user":
        _set_blocked(state, "other_user_data_denied", requested_scope, "malicious")
    elif requested_scope == "unknown":
        _set_blocked(state, "ambiguous_user_context_denied", requested_scope, "general_false")
    elif state["normalized_intent"] == "unsupported":
        _set_blocked(state, "unsupported_query", "unsupported", "general_false")
    else:
        _set_allowed(state)

    state["security_response"] = generate_security_llm_response(state)
    _LOGGER.info(
        "security_decision user_id=%s decision=%s scope=%s intent=%s risk=%s reason=%s",
        state.get("user_id"),
        state.get("security_decision"),
        state.get("requested_scope"),
        state.get("normalized_intent"),
        state.get("security_risk_type"),
        state.get("security_reason"),
    )
    return state
