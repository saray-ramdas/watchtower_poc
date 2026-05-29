from fastapi import APIRouter, Depends, HTTPException
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
)
from ..agents.master_agent import run_master_agent
from ..agents.prize_money_agent import run_prize_money_agent
from ..agents.response_agent import run_response_agent
from ..agents.savings_agent import run_savings_agent
from ..db.session import get_db
from ..graph.state import EligibilityState, build_initial_state

router = APIRouter(prefix="/api/v1", tags=["eligibility"])


def _run_final_agent_flow(user_id: str, query: str, db: Session) -> EligibilityState:
    state = build_initial_state(user_id, query)
    state = run_master_agent(state)

    if state.get("guardrail_status") == "blocked":
        return run_response_agent(state)

    try:
        state = run_savings_agent(state, db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc.__class__.__name__}",
        ) from exc

    if state.get("decision_reason") == "user_not_found":
        raise HTTPException(status_code=404, detail="User not found")

    if state.get("normalized_intent") == "lottery_eligibility":
        state = run_prize_money_agent(state)
    else:
        state["decision_reason"] = "savings_data_answered_requested_intent"

    return run_response_agent(state)


def _to_final_response(state: EligibilityState) -> FinalAgentResponse:
    return FinalAgentResponse(
        user_id=state["user_id"],
        input_query=state["original_query"],
        response=state["final_response"],
    )


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
    state = run_master_agent(state)

    try:
        result = run_savings_agent(state, db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc.__class__.__name__}",
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
