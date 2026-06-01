from fastapi import APIRouter, Depends, HTTPException
import re
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .schemas import (
    FinalAgentRequest,
    FinalAgentResponse,
    EligibilityRequest,
    EligibilityResponse,
    PrizeMoneyAgentRequest,
    PrizeMoneyAgentResponse,
    ResponseAgentRequest,
    ResponseAgentResponse,
    SavingsAgentRequest,
    SavingsAgentResponse,
    SecurityCheckRequest,
    SecurityCheckResponse,
    PIIMaskRequest,
    PIIMaskResponse,
    PIIMaskedItem,
    FinalSecurityPIIRequest,
    FinalSecurityPIIResponse,
    PIISavingsEligibilityRequest,
    PIISavingsEligibilityResponse,
    FinalOfFinalRequest,
    FinalOfFinalResponse,
)
from ..agents.master_agent import run_master_agent
from ..agents.prize_money_agent import run_prize_money_agent
from ..agents.response_agent import run_response_agent
from ..clients.llm_client import LLMGenerationError
from ..agents.savings_agent import run_savings_agent
from ..agents.security_pii_agent import run_security_pii_agent
from ..db.session import get_db
from ..graph.workflow import run_workflow
from ..graph.state import EligibilityState, build_initial_state
from ..services.pii_vault_service import (
    detokenize_masked_query_from_vault,
    detokenize_text_from_vault,
    store_pii_entities_in_vault,
)

router = APIRouter(prefix="/api/v1", tags=["eligibility"])
_NAME_PATTERN = re.compile(r"\bmy name is\s+([a-zA-Z][a-zA-Z\s'-]{0,49})", re.IGNORECASE)
_MASKED_NAME_PATTERN = re.compile(r"\bmy name is\s+(<PII_[A-Z0-9_]+>)", re.IGNORECASE)
_USER_ID_TOKEN = "<USER_ID_MASKED>"
_BALANCE_TOKEN = "<BALANCE_MASKED>"
_YEARS_TOKEN = "<YEARS_IN_BANK_MASKED>"


def _run_final_agent_flow(user_id: str, query: str, db: Session) -> EligibilityState:
    state = build_initial_state(user_id, query)
    try:
        state = run_workflow(state, db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc.__class__.__name__}",
        ) from exc
    except LLMGenerationError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM response generation failed: {exc}",
        ) from exc

    if state.get("decision_reason") == "user_not_found":
        raise HTTPException(status_code=404, detail="User not found")
    return state


def _to_final_response(state: EligibilityState) -> FinalAgentResponse:
    return FinalAgentResponse(
        user_id=state["user_id"],
        input_query=state["original_query"],
        response=state["final_response"],
    )


def _split_security_response(security_response: str) -> tuple[str, str]:
    lines = [line.strip() for line in security_response.splitlines() if line.strip()]
    output = lines[0].lower() if lines else "no"
    reason = lines[1] if len(lines) > 1 else ""

    for prefix in ("Reason:", "Warning:"):
        if reason.lower().startswith(prefix.lower()):
            reason = reason[len(prefix) :].strip()
            break

    return output, reason


def _run_security_check_response(payload: SecurityCheckRequest) -> SecurityCheckResponse:
    state = build_initial_state(payload.user_id, payload.query)

    try:
        result = run_master_agent(state)
    except LLMGenerationError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM security response generation failed: {exc}",
        ) from exc

    output, reason = _split_security_response(result["security_response"])
    return SecurityCheckResponse(
        output=output,
        reason=reason,
        flag=(
            "warning"
            if result.get("security_risk_type") == "malicious"
            else "no warning"
        ),
    )


def _infer_intent_from_query(query: str) -> str:
    normalized = query.lower()
    if any(term in normalized for term in ("lottery", "eligible", "eligibility", "qualify", "qualified", "prize")):
        return "lottery_eligibility"
    if any(term in normalized for term in ("balance", "savings", "account amount", "how much money")):
        return "bank_balance"
    if any(term in normalized for term in ("years", "tenure", "how long", "with the bank")):
        return "bank_tenure"
    return "unsupported"


def _extract_customer_name(query: str) -> str | None:
    match = _NAME_PATTERN.search(query)
    if not match:
        return None
    return match.group(1).strip()


def _extract_masked_customer_name(query: str) -> str | None:
    match = _MASKED_NAME_PATTERN.search(query)
    if not match:
        return None
    return match.group(1).strip()


def _restore_internal_masked_fields(response_text: str, state: EligibilityState) -> str:
    restored = response_text
    user_id = state.get("user_id")
    balance = state.get("balance")
    years_in_bank = state.get("years_in_bank")
    if user_id is not None:
        restored = restored.replace(_USER_ID_TOKEN, str(user_id))
    if balance is not None:
        restored = restored.replace(_BALANCE_TOKEN, str(balance))
    if years_in_bank is not None:
        restored = restored.replace(_YEARS_TOKEN, str(years_in_bank))
    return restored


@router.post("/eligibility", response_model=EligibilityResponse)
def check_eligibility(
    payload: EligibilityRequest,
    db: Session = Depends(get_db),
) -> EligibilityResponse:
    state = _run_final_agent_flow(payload.user_id, payload.query, db)
    final_response = _to_final_response(state)
    return EligibilityResponse(**final_response.model_dump())


@router.post("/agents/savings", response_model=SavingsAgentResponse)
def test_savings_agent(
    payload: SavingsAgentRequest,
    db: Session = Depends(get_db),
) -> SavingsAgentResponse:
    state = build_initial_state(payload.user_id, payload.query)

    try:
        state = run_master_agent(state)
        if state.get("guardrail_status") == "blocked":
            return SavingsAgentResponse(
                user_id=state["user_id"],
                original_query=state["original_query"],
                normalized_intent=state["normalized_intent"],
                balance=None,
                years_in_bank=None,
            )

        result = run_savings_agent(state, db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc.__class__.__name__}",
        ) from exc
    except LLMGenerationError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM response generation failed: {exc}",
        ) from exc

    return SavingsAgentResponse(
        user_id=result["user_id"],
        original_query=result["original_query"],
        normalized_intent=result["normalized_intent"],
        balance=result.get("balance"),
        years_in_bank=result.get("years_in_bank"),
    )


@router.post("/agents/prize-money", response_model=PrizeMoneyAgentResponse)
def test_prize_money_agent(
    payload: PrizeMoneyAgentRequest,
) -> PrizeMoneyAgentResponse:
    state = {
        "balance": payload.balance,
        "years_in_bank": payload.years_in_bank,
    }
    result = run_prize_money_agent(state)
    balance_requirement_met = result["balance"] > 50000
    years_requirement_met = result["years_in_bank"] >= 3

    return PrizeMoneyAgentResponse(
        balance=result["balance"],
        years_in_bank=result["years_in_bank"],
        eligible=result["eligible"],
        decision_reason=result["decision_reason"],
        balance_requirement_status=(
            "Savings balance is above the required limit."
            if balance_requirement_met
            else "Savings balance is not above the required limit."
        ),
        years_requirement_status=(
            "Years in bank meet the requirement."
            if years_requirement_met
            else "Years in bank do not meet the requirement."
        ),
    )


@router.post("/agents/response", response_model=ResponseAgentResponse)
def test_response_agent(
    payload: ResponseAgentRequest,
) -> ResponseAgentResponse:
    state = {
        "original_query": payload.query,
        "normalized_intent": "lottery_eligibility",
        "balance": payload.balance,
        "years_in_bank": payload.years_in_bank,
        "eligible": payload.eligible,
        "decision_reason": payload.decision_reason,
    }
    result = run_response_agent(state)

    return ResponseAgentResponse(
        original_query=result["original_query"],
        balance=result["balance"],
        years_in_bank=result["years_in_bank"],
        eligible=result["eligible"],
        decision_reason=result["decision_reason"],
        final_response=result["final_response"],
    )


@router.post("/agents/final", response_model=FinalAgentResponse)
def test_final_agent(
    payload: FinalAgentRequest,
    db: Session = Depends(get_db),
) -> FinalAgentResponse:
    state = _run_final_agent_flow(payload.user_id, payload.query, db)
    return _to_final_response(state)


@router.post("/security-check", response_model=SecurityCheckResponse)
def check_security(
    payload: SecurityCheckRequest,
) -> SecurityCheckResponse:
    return _run_security_check_response(payload)


@router.post("/pii/mask", response_model=PIIMaskResponse)
def mask_pii(
    payload: PIIMaskRequest,
    db: Session = Depends(get_db),
) -> PIIMaskResponse:
    try:
        state = run_security_pii_agent({"user_id": "user1", "original_query": payload.query})
        result = store_pii_entities_in_vault(
            masked_query=state.get("masked_query", payload.query),
            pii_entities=state.get("pii_entities", []),
            db=db,
        )
    except LLMGenerationError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM PII detection failed: {exc}",
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc.__class__.__name__}",
        ) from exc

    return PIIMaskResponse(
        input_query=payload.query,
        masked_query=result.masked_query,
        masked_items=[
            PIIMaskedItem(token=item.token, pii_type=item.pii_type)
            for item in result.masked_items
        ],
    )


@router.post("/final-secu-pii", response_model=FinalSecurityPIIResponse)
def final_security_and_pii(
    payload: FinalSecurityPIIRequest,
    db: Session = Depends(get_db),
) -> FinalSecurityPIIResponse:
    try:
        state = run_security_pii_agent(
            {"user_id": payload.user_id, "original_query": payload.query}
        )
        vault_result = store_pii_entities_in_vault(
            masked_query=state.get("masked_query", payload.query),
            pii_entities=state.get("pii_entities", []),
            db=db,
        )
    except LLMGenerationError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM security/PII processing failed: {exc}",
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc.__class__.__name__}",
        ) from exc

    output, reason = _split_security_response(state.get("security_response", "no"))
    return FinalSecurityPIIResponse(
        user_id=payload.user_id,
        input_query=payload.query,
        security_output=output,
        security_reason=reason,
        security_flag=(
            "warning" if state.get("security_risk_type") == "malicious" else "no warning"
        ),
        masked_query=vault_result.masked_query,
        masked_items=[
            PIIMaskedItem(token=item.token, pii_type=item.pii_type)
            for item in vault_result.masked_items
        ],
    )


@router.post("/agents/pii-savings-eligibility-response", response_model=PIISavingsEligibilityResponse)
def pii_savings_eligibility_response(
    payload: PIISavingsEligibilityRequest,
    db: Session = Depends(get_db),
) -> PIISavingsEligibilityResponse:
    try:
        unmasked_query = detokenize_masked_query_from_vault(payload.masked_query, db)
        # Input is already masked; keep it as source for LLM-safe output.
        remasked_query = payload.masked_query
        intent = _infer_intent_from_query(unmasked_query)
        state: EligibilityState = build_initial_state(payload.user_id, remasked_query)
        state["normalized_intent"] = intent
        state["keep_masked_output"] = True
        masked_customer_name = _extract_masked_customer_name(remasked_query)
        if masked_customer_name:
            state["customer_name"] = masked_customer_name
        state = run_savings_agent(state, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc.__class__.__name__}",
        ) from exc

    if state.get("decision_reason") == "user_not_found":
        raise HTTPException(status_code=404, detail="User not found")

    eligible: bool | None = None
    balance = state.get("balance")
    years_in_bank = state.get("years_in_bank")
    actual_query_output = "Unsupported query. Ask for balance, banking tenure, or lottery eligibility."

    if intent == "lottery_eligibility":
        prize_state = run_prize_money_agent(state)
        eligible = prize_state.get("eligible")
        state["eligible"] = bool(eligible)
        state["decision_reason"] = prize_state.get("decision_reason", state.get("decision_reason", ""))
        state = run_response_agent(state)
        actual_query_output = state.get("final_response", "")
    elif intent in {"bank_balance", "bank_tenure"}:
        state["decision_reason"] = "savings_data_answered_requested_intent"
        state = run_response_agent(state)
        actual_query_output = state.get("final_response", actual_query_output)
    else:
        state["decision_reason"] = "unsupported_query"
        state = run_response_agent(state)
        actual_query_output = state.get("final_response", actual_query_output)

    user_query_output = _restore_internal_masked_fields(actual_query_output, state)
    user_query_output = detokenize_text_from_vault(user_query_output, db, strict=False)

    return PIISavingsEligibilityResponse(
        remasked_query=remasked_query,
        unmasked_query=unmasked_query,
        balance=balance,
        years_in_bank=years_in_bank,
        eligible=eligible,
        actual_query_output=actual_query_output,
        user_query_output=user_query_output,
    )


@router.post("/final-of-final", response_model=FinalOfFinalResponse)
def final_of_final(
    payload: FinalOfFinalRequest,
    db: Session = Depends(get_db),
) -> FinalOfFinalResponse:
    security_pii_result = final_security_and_pii(
        FinalSecurityPIIRequest(user_id=payload.user_id, query=payload.query),
        db,
    )
    savings_eligibility_result = pii_savings_eligibility_response(
        PIISavingsEligibilityRequest(
            user_id=payload.user_id,
            masked_query=security_pii_result.masked_query,
        ),
        db,
    )

    return FinalOfFinalResponse(
        user_id=payload.user_id,
        input_query=payload.query,
        security_output=security_pii_result.security_output,
        security_reason=security_pii_result.security_reason,
        security_flag=security_pii_result.security_flag,
        masked_query=security_pii_result.masked_query,
        masked_items=security_pii_result.masked_items,
        remasked_query=savings_eligibility_result.remasked_query,
        unmasked_query=savings_eligibility_result.unmasked_query,
        balance=savings_eligibility_result.balance,
        years_in_bank=savings_eligibility_result.years_in_bank,
        eligible=savings_eligibility_result.eligible,
        actual_query_output=savings_eligibility_result.actual_query_output,
        user_query_output=savings_eligibility_result.user_query_output,
    )
