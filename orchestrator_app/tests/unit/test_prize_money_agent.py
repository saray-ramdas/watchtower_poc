from orchestrator_app.app.agents.prize_money_agent import run_prize_money_agent


def test_prize_money_agent_eligible() -> None:
    state = {"balance": 75000.0, "years_in_bank": 4}
    result = run_prize_money_agent(state)
    assert result["eligible"] is True


def test_prize_money_agent_not_eligible_at_balance_boundary() -> None:
    state = {"balance": 50000.0, "years_in_bank": 4}
    result = run_prize_money_agent(state)
    assert result["eligible"] is False


def test_prize_money_agent_tenure_boundary_is_valid() -> None:
    state = {"balance": 60000.0, "years_in_bank": 3}
    result = run_prize_money_agent(state)
    assert result["eligible"] is True
