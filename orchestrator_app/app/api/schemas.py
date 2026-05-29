from pydantic import BaseModel, Field


class EligibilityRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="Unique customer identifier")
    query: str = Field(..., min_length=1, description="User query text")


class EligibilityResponse(BaseModel):
    user_id: str
    input_query: str
    response: str


class SavingsAgentRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="Unique customer identifier")
    query: str = Field(
        "check_savings",
        min_length=1,
        description="Test query text passed into the initial agent state",
    )


class SavingsAgentResponse(BaseModel):
    user_id: str
    original_query: str
    normalized_intent: str = "lottery_eligibility"
    balance: float | None = None
    years_in_bank: int | None = None


class PrizeMoneyAgentRequest(BaseModel):
    balance: float = Field(..., description="Customer savings balance")
    years_in_bank: int = Field(..., ge=0, description="Number of years in bank")


class PrizeMoneyAgentResponse(BaseModel):
    balance: float
    years_in_bank: int
    eligible: bool
    decision_reason: str
    balance_requirement_status: str
    years_requirement_status: str


class ResponseAgentRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User query text")
    balance: float = Field(..., description="Customer savings balance")
    years_in_bank: int = Field(..., ge=0, description="Number of years in bank")
    eligible: bool
    decision_reason: str = Field(..., min_length=1, description="Prize money agent reason")


class ResponseAgentResponse(BaseModel):
    original_query: str
    balance: float
    years_in_bank: int
    eligible: bool
    decision_reason: str
    final_response: str


class FinalAgentRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="Unique customer identifier")
    query: str = Field(..., min_length=1, description="User query text")


class FinalAgentResponse(BaseModel):
    user_id: str
    input_query: str
    response: str
