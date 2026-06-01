from typing import TypedDict


class EligibilityState(TypedDict, total=False):
    user_id: str
    original_query: str
    security_decision: str
    security_reason: str
    security_response: str
    security_risk_type: str
    requested_scope: str
    mentioned_user_ids: list[str]
    normalized_intent: str
    guardrail_status: str
    balance: float
    years_in_bank: int
    eligible: bool
    decision_reason: str
    final_response: str
    response_source: str


def build_initial_state(user_id: str, original_query: str) -> EligibilityState:
    return {
        "user_id": user_id,
        "original_query": original_query,
        "security_decision": "pending",
        "security_reason": "",
        "security_risk_type": "unknown",
        "requested_scope": "unknown",
        "mentioned_user_ids": [],
        "normalized_intent": "unknown",
        "guardrail_status": "pending",
    }
