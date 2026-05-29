import json
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from ..graph.state import EligibilityState

try:
    from jinja2 import Template
except ImportError:
    Template = None


_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "response_prompt.j2"


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


def _fallback_response(state: EligibilityState) -> str:
    balance = state.get("balance")
    years_in_bank = state.get("years_in_bank")
    eligible = state.get("eligible", False)
    decision_reason = state.get("decision_reason")
    intent = state.get("normalized_intent")

    if intent == "bank_balance":
        return (
            "Answer: Your current savings balance is "
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
            "Answer: You have been with the bank for "
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
            "Answer: I cannot handle that request through this endpoint.\n\n"
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
            "Verdict: Yes, you are eligible for the lottery.\n\n"
            "Details:\n"
            f"- Savings balance reviewed by the Savings Agent: {balance}.\n"
            f"- Years with the bank reviewed by the Savings Agent: {years_in_bank}.\n"
            f"- Prize Money Agent reasoning: {decision_reason}\n\n"
            "Why this decision was made:\n"
            f"{balance_status} {tenure_status} Since both requirements are satisfied, "
            "you qualify for the lottery."
        )

    return (
        "Verdict: No, you are not eligible for the lottery.\n\n"
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
        return not any(term in normalized_output for term in blocked_terms)

    if intent == "unsupported":
        sensitive_terms = ("password", "secret", "system prompt", "developer message")
        return not any(term in normalized_output for term in sensitive_terms)

    return True


def _generate_with_configured_llm(prompt: str) -> str | None:
    """
    Use a generic JSON LLM endpoint when configured.

    Set LLM_API_URL and optionally LLM_API_KEY. The endpoint is expected to accept
    {"prompt": "..."} and return either {"response": "..."} or {"text": "..."}.
    """
    api_url = os.getenv("LLM_API_URL")
    if not api_url:
        return None

    payload = json.dumps({"prompt": prompt}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("LLM_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = Request(api_url, data=payload, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=15) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError):
        return None

    generated = body.get("response") or body.get("text")
    if not isinstance(generated, str) or not generated.strip():
        return None
    return generated.strip()


def run_response_agent(state: EligibilityState) -> EligibilityState:
    """
    Generate the final user-facing response from prior agent outputs.
    """
    prompt = _build_prompt(state)
    generated = _generate_with_configured_llm(prompt)
    if generated and _passes_output_guardrails(state, generated):
        state["final_response"] = generated
        return state

    state["final_response"] = _fallback_response(state)
    return state
