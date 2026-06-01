from orchestrator_app.app.agents.response_agent import run_response_agent


def _base_state() -> dict:
    return {
        "user_id": "u1001",
        "original_query": "am i eligible?",
        "normalized_intent": "lottery_eligibility",
        "balance": 70000.0,
        "years_in_bank": 4,
        "eligible": True,
        "decision_reason": "User meets balance and tenure requirements.",
    }


def test_response_agent_uses_llm_when_available(monkeypatch) -> None:
    monkeypatch.setattr(
        "orchestrator_app.app.agents.response_agent.generate_llm_response",
        lambda prompt: "LLM answer",
    )
    result = run_response_agent(_base_state())
    assert result["final_response"] == "LLM answer"
    assert result["response_source"] == "llm"


def test_response_agent_uses_fallback_when_llm_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        "orchestrator_app.app.agents.response_agent.generate_llm_response",
        lambda prompt: None,
    )
    result = run_response_agent(_base_state())
    assert result["response_source"] == "fallback"
    assert "fall back message" in result["final_response"].lower()
