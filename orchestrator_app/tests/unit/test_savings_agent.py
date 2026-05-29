from types import SimpleNamespace

from orchestrator_app.app.agents.savings_agent import run_savings_agent


def test_savings_agent_returns_balance_and_years(monkeypatch) -> None:
    monkeypatch.setattr(
        "orchestrator_app.app.agents.savings_agent.get_customer_balance_by_user_id",
        lambda db, user_id: 82000.0,
    )
    monkeypatch.setattr(
        "orchestrator_app.app.agents.savings_agent.get_customer_years_in_bank_by_user_id",
        lambda db, user_id: 5,
    )

    state = {"user_id": "u1001", "original_query": "what is my balance?"}
    result = run_savings_agent(state, SimpleNamespace())
    assert result["balance"] == 82000.0
    assert result["years_in_bank"] == 5
    assert result["decision_reason"] == "savings_loaded"


def test_savings_agent_user_not_found(monkeypatch) -> None:
    monkeypatch.setattr(
        "orchestrator_app.app.agents.savings_agent.get_customer_balance_by_user_id",
        lambda db, user_id: None,
    )
    monkeypatch.setattr(
        "orchestrator_app.app.agents.savings_agent.get_customer_years_in_bank_by_user_id",
        lambda db, user_id: None,
    )

    state = {"user_id": "missing", "original_query": "what is my balance?"}
    result = run_savings_agent(state, SimpleNamespace())
    assert result["eligible"] is False
    assert result["decision_reason"] == "user_not_found"
