from pathlib import Path

from ..clients.llm_client import LLMGenerationError, generate_llm_response
from ..graph.state import EligibilityState

try:
    from jinja2 import Template
except ImportError:
    Template = None


_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "response_prompt.j2"
_USER_ID_TOKEN = "<USER_ID_MASKED>"
_BALANCE_TOKEN = "<BALANCE_MASKED>"
_YEARS_TOKEN = "<YEARS_IN_BANK_MASKED>"


def _render_template(template_path: Path, context: EligibilityState) -> str | None:
    if Template is None or not template_path.exists():
        return None

    template = Template(template_path.read_text(encoding="utf-8"))
    return template.render(**context)


def _build_prompt(state: EligibilityState) -> str:
    rendered = _render_template(_PROMPT_PATH, state)
    if rendered:
        return rendered

    return (
        "Create a clear, customer-facing response for a banking customer who asked this query: "
        f"{state.get('original_query', '')!r}. "
        f"Intent: {state.get('normalized_intent')}. "
        f"Savings balance: {state.get('balance')}. "
        f"Years in bank: {state.get('years_in_bank')}. "
        f"Eligibility: {state.get('eligible')}. "
        f"Decision reason: {state.get('decision_reason')}. "
        "Answer only the requested intent. Do not mention lottery eligibility for balance "
        "or tenure questions."
    )


def _build_masked_prompt_state(state: EligibilityState) -> tuple[EligibilityState, dict[str, str]]:
    masked_state = dict(state)
    replacements: dict[str, str] = {}

    user_id = state.get("user_id")
    if user_id is not None:
        masked_state["user_id"] = _USER_ID_TOKEN
        replacements[_USER_ID_TOKEN] = str(user_id)

    balance = state.get("balance")
    if balance is not None:
        masked_state["balance"] = _BALANCE_TOKEN
        replacements[_BALANCE_TOKEN] = str(balance)

    years_in_bank = state.get("years_in_bank")
    if years_in_bank is not None:
        masked_state["years_in_bank"] = _YEARS_TOKEN
        replacements[_YEARS_TOKEN] = str(years_in_bank)

    return masked_state, replacements


def _unmask_generated_response(generated: str, replacements: dict[str, str]) -> str:
    restored = generated
    for token, value in replacements.items():
        restored = restored.replace(token, value)
    return restored


def _fallback_response(state: EligibilityState) -> str:
    balance = state.get("balance")
    years_in_bank = state.get("years_in_bank")
    eligible = state.get("eligible", False)
    decision_reason = state.get("decision_reason")
    intent = state.get("normalized_intent")
    fallback_prefix = "this is a fall back message\n\n"

    if intent == "bank_balance":
        return (
            fallback_prefix
            + "Answer: Your current savings balance is "
            f"{balance}.\n\n"
            "Details:\n"
            f"- Savings Agent result: balance = {balance}.\n"
            f"- User ID checked: {state.get('user_id')}.\n\n"
            "Reasoning:\n"
            "Your question asked for your bank balance, so I used the Savings Agent data "
            "to answer with the account value available for your user ID."
        )

    if intent == "bank_tenure":
        return (
            fallback_prefix
            + "Answer: You have been with the bank for "
            f"{years_in_bank} years.\n\n"
            "Details:\n"
            f"- Savings Agent result: years_in_bank = {years_in_bank}.\n"
            f"- User ID checked: {state.get('user_id')}.\n\n"
            "Reasoning:\n"
            "Your question asked about banking tenure, so I used the tenure value from "
            "the Savings Agent for your user ID."
        )

    if intent == "unsupported":
        return (
            fallback_prefix
            + "Answer: I cannot handle that request through this endpoint.\n\n"
            "Details:\n"
            f"- Guardrail status: {state.get('guardrail_status')}.\n"
            f"- Reason: {decision_reason}.\n\n"
            "Reasoning:\n"
            "This endpoint only supports bank balance, banking tenure, and lottery "
            "eligibility questions for the supplied user."
        )

    balance_status = (
        "Your savings balance is above the required threshold of 50000."
        if balance is not None and float(balance) > 50000
        else "Your savings balance is not above the required threshold of 50000."
    )
    tenure_status = (
        "Your banking tenure meets the minimum requirement of 3 years."
        if years_in_bank is not None and years_in_bank >= 3
        else "Your banking tenure does not meet the minimum requirement of 3 years."
    )

    if eligible:
        return (
            fallback_prefix
            + "Verdict: Yes, you are eligible for the lottery.\n\n"
            "Details:\n"
            f"- Savings balance reviewed by the Savings Agent: {balance}.\n"
            f"- Years with the bank reviewed by the Savings Agent: {years_in_bank}.\n"
            f"- Prize Money Agent reasoning: {decision_reason}\n\n"
            "Why this decision was made:\n"
            f"{balance_status} {tenure_status} Since both requirements are satisfied, "
            "you qualify for the lottery."
        )

    return (
        fallback_prefix
        + "Verdict: No, you are not eligible for the lottery.\n\n"
        "Details:\n"
        f"- Savings balance reviewed by the Savings Agent: {balance}.\n"
        f"- Years with the bank reviewed by the Savings Agent: {years_in_bank}.\n"
        f"- Prize Money Agent reasoning: {decision_reason}\n\n"
        "Why this decision was made:\n"
        f"{balance_status} {tenure_status} Because one or more requirements are not "
        "satisfied, you do not currently qualify for the lottery."
    )


def _passes_output_guardrails(state: EligibilityState, generated: str) -> bool:
    normalized_output = generated.lower()
    intent = state.get("normalized_intent")

    if intent in {"bank_balance", "bank_tenure"}:
        blocked_terms = ("eligible", "eligibility", "lottery", "qualify", "qualified")
        if any(term in normalized_output for term in blocked_terms):
            return False

    if intent == "bank_balance":
        tenure_terms = ("years in bank", "bank tenure", "with the bank for")
        return not any(term in normalized_output for term in tenure_terms)

    if intent == "bank_tenure":
        balance_terms = ("balance", "savings", "$", "50,001", "50001")
        return not any(term in normalized_output for term in balance_terms)

    if intent == "unsupported":
        sensitive_terms = ("password", "secret", "system prompt", "developer message")
        return not any(term in normalized_output for term in sensitive_terms)

    return True


def run_response_agent(state: EligibilityState) -> EligibilityState:
    """
    Generate the final user-facing response from prior agent outputs.
    """
    masked_state, replacements = _build_masked_prompt_state(state)
    prompt = _build_prompt(masked_state)
    generated = generate_llm_response(prompt)

    if generated is None:
        state["final_response"] = _fallback_response(state)
        state["response_source"] = "fallback"
        return state

    keep_masked_output = bool(state.get("keep_masked_output"))
    if _passes_output_guardrails(state, generated):
        state["final_response"] = (
            generated
            if keep_masked_output
            else _unmask_generated_response(generated, replacements)
        )
        state["response_source"] = "llm"
        return state

    retry_prompt = (
        f"{prompt}\n\n"
        "The previous draft violated the output guardrails. Regenerate the response. "
        f"Only answer the {state.get('normalized_intent')} intent. "
        "Use only masked placeholders for sensitive data fields. "
        "Do not include any unrelated fields or policy areas."
    )
    regenerated = generate_llm_response(retry_prompt)
    if regenerated and _passes_output_guardrails(state, regenerated):
        state["final_response"] = (
            regenerated
            if keep_masked_output
            else _unmask_generated_response(regenerated, replacements)
        )
        state["response_source"] = "llm"
        return state

    state["final_response"] = _fallback_response(state)
    state["response_source"] = "fallback"
    return state
