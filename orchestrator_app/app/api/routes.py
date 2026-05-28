from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .schemas import EligibilityRequest, EligibilityResponse
from ..db.models import CustomerLotteryProfile
from ..db.session import get_db

router = APIRouter(prefix="/api/v1", tags=["eligibility"])


@router.post("/eligibility", response_model=EligibilityResponse)
def check_eligibility(
    payload: EligibilityRequest,
    db: Session = Depends(get_db),
) -> EligibilityResponse:
    try:
        customer = (
            db.query(CustomerLotteryProfile)
            .filter(CustomerLotteryProfile.user_id == payload.user_id)
            .first()
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc.__class__.__name__}",
        ) from exc

    if customer is None:
        raise HTTPException(status_code=404, detail="User not found")

    eligible = (float(customer.balance) > 50000) and (customer.years_in_bank >= 3)
    decision_reason = (
        "User meets balance and tenure requirements."
        if eligible
        else "User does not meet one or more eligibility requirements."
    )
    final_response = (
        "Yes, you are eligible for the lottery."
        if eligible
        else "No, you are not eligible for the lottery."
    )

    return EligibilityResponse(
        user_id=payload.user_id,
        balance=float(customer.balance),
        years_in_bank=customer.years_in_bank,
        eligible=eligible,
        decision_reason=decision_reason,
        final_response=final_response,
    )
