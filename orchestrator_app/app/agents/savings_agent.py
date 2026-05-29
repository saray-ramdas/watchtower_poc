from sqlalchemy.orm import Session

from ..graph.state import EligibilityState
from ..tools.banking_tools import (
	get_customer_balance_by_user_id,
	get_customer_years_in_bank_by_user_id,
)


def run_savings_agent(state: EligibilityState, db: Session) -> EligibilityState:
	"""
	Populate the state with `balance` and `years_in_bank` for `user_id`.
	If user is missing, set a predictable result in `decision_reason`.
	"""
	user_id = state.get("user_id")
	if not user_id:
		state["balance"] = None
		state["years_in_bank"] = None
		state["eligible"] = False
		state["decision_reason"] = "missing_user_id"
		return state

	balance = get_customer_balance_by_user_id(db, user_id)
	years_in_bank = get_customer_years_in_bank_by_user_id(db, user_id)
	if balance is None or years_in_bank is None:
		state["balance"] = None
		state["years_in_bank"] = None
		state["eligible"] = False
		state["decision_reason"] = "user_not_found"
		return state

	state["balance"] = balance
	state["years_in_bank"] = years_in_bank
	state["decision_reason"] = "savings_loaded"
	return state

