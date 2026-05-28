from pydantic import BaseModel, Field


class EligibilityRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="Unique customer identifier")
    query: str = Field(..., min_length=1, description="User query text")


class EligibilityResponse(BaseModel):
    user_id: str
    normalized_intent: str = "lottery_eligibility"
    balance: float | None = None
    years_in_bank: int | None = None
    eligible: bool
    decision_reason: str
    final_response: str
