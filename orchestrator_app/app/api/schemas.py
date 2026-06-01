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


class SecurityCheckRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User query text")
    user_id: str = Field(
        "user1",
        min_length=1,
        description="Authenticated user id for testing the security gate",
    )


class SecurityCheckResponse(BaseModel):
    output: str
    reason: str
    flag: str


class PIIMaskRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User query text to redact")


class PIIMaskedItem(BaseModel):
    token: str
    pii_type: str


class PIIMaskResponse(BaseModel):
    input_query: str
    masked_query: str
    masked_items: list[PIIMaskedItem]


class FinalSecurityPIIRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="Authenticated user id")
    query: str = Field(..., min_length=1, description="User query text")


class FinalSecurityPIIResponse(BaseModel):
    user_id: str
    input_query: str
    security_output: str
    security_reason: str
    security_flag: str
    masked_query: str
    masked_items: list[PIIMaskedItem]


class PIISavingsEligibilityRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="Authenticated user id")
    masked_query: str = Field(..., min_length=1, description="Tokenized query text")


class PIISavingsEligibilityResponse(BaseModel):
    remasked_query: str
    unmasked_query: str
    balance: float | None = None
    years_in_bank: int | None = None
    eligible: bool | None = None
    actual_query_output: str
    user_query_output: str


class FinalOfFinalRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="Authenticated user id")
    query: str = Field(..., min_length=1, description="User query text")


class FinalOfFinalResponse(BaseModel):
    user_id: str
    input_query: str
    security_output: str
    security_reason: str
    security_flag: str
    masked_query: str
    masked_items: list[PIIMaskedItem]
    remasked_query: str
    unmasked_query: str
    balance: float | None = None
    years_in_bank: int | None = None
    eligible: bool | None = None
    actual_query_output: str
    user_query_output: str
