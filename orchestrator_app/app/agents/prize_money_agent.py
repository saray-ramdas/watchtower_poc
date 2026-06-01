from ..graph.state import EligibilityState


def run_prize_money_agent(state: EligibilityState) -> EligibilityState:
    """
    Decide lottery eligibility from balance and years in bank.
    """
    balance = state.get("balance")
    years_in_bank = state.get("years_in_bank")

    if balance is None or years_in_bank is None:
        state["eligible"] = False
        state["decision_reason"] = "missing_savings_data"
        return state

    eligible = float(balance) > 50000 and years_in_bank >= 3
    state["eligible"] = eligible
    state["decision_reason"] = (
        "User meets balance and tenure requirements."
        if eligible
        else "User does not meet one or more eligibility requirements."
    )
    return state
