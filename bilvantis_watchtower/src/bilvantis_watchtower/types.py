from typing import Callable, TypedDict


class SecurityState(TypedDict, total=False):
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
    decision_reason: str


SecurityLLMGenerator = Callable[[str], str | None]


class PIIDetectedEntity(TypedDict):
    value: str
    pii_type: str


class SecurityPIIState(SecurityState, total=False):
    masked_query: str
    pii_entities: list[PIIDetectedEntity]
