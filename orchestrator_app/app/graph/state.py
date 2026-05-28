from typing import TypedDict


class EligibilityState(TypedDict, total=False):
    user_id: str
    original_query: str
    normalized_intent: str
    balance: float
    years_in_bank: int
    eligible: bool
    decision_reason: str
    final_response: str


def build_initial_state(user_id: str, original_query: str) -> EligibilityState:
    return {
        "user_id": user_id,
        "original_query": original_query,
        "normalized_intent": "lottery_eligibility",
    }
