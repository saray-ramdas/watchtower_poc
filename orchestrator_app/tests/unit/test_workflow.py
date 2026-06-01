from types import SimpleNamespace

from orchestrator_app.app.graph.state import build_initial_state
from orchestrator_app.app.graph.workflow import run_workflow


def test_workflow_balance_intent_path(monkeypatch) -> None:
    monkeypatch.setattr(
        "orchestrator_app.app.graph.workflow.run_master_agent",
        lambda state: {**state, "normalized_intent": "bank_balance", "guardrail_status": "allowed"},
    )
    monkeypatch.setattr(
        "orchestrator_app.app.graph.workflow.run_savings_agent",
        lambda state, db: {**state, "balance": 65000.0, "years_in_bank": 2, "decision_reason": "savings_loaded"},
    )
    monkeypatch.setattr(
        "orchestrator_app.app.graph.workflow.run_response_agent",
        lambda state: {**state, "final_response": "balance response"},
    )

    state = build_initial_state("u1", "what is my balance?")
    result = run_workflow(state, SimpleNamespace())
    assert result["normalized_intent"] == "bank_balance"
    assert result["final_response"] == "balance response"


def test_workflow_lottery_path(monkeypatch) -> None:
    monkeypatch.setattr(
        "orchestrator_app.app.graph.workflow.run_master_agent",
        lambda state: {**state, "normalized_intent": "lottery_eligibility", "guardrail_status": "allowed"},
    )
    monkeypatch.setattr(
        "orchestrator_app.app.graph.workflow.run_savings_agent",
        lambda state, db: {**state, "balance": 70000.0, "years_in_bank": 4, "decision_reason": "savings_loaded"},
    )
    monkeypatch.setattr(
        "orchestrator_app.app.graph.workflow.run_prize_money_agent",
        lambda state: {**state, "eligible": True, "decision_reason": "eligible"},
    )
    monkeypatch.setattr(
        "orchestrator_app.app.graph.workflow.run_response_agent",
        lambda state: {**state, "final_response": "eligible response"},
    )

    state = build_initial_state("u1", "am i eligible for lottery?")
    result = run_workflow(state, SimpleNamespace())
    assert result["eligible"] is True
    assert result["final_response"] == "eligible response"
