from fastapi.testclient import TestClient

from orchestrator_app.app.api import routes
from orchestrator_app.app.main import app


client = TestClient(app)


def test_api_eligibility_happy_path(monkeypatch) -> None:
    monkeypatch.setattr(
        routes,
        "run_workflow",
        lambda state, db: {
            **state,
            "final_response": "Yes, you are eligible.",
        },
    )
    app.dependency_overrides[routes.get_db] = lambda: object()
    try:
        response = client.post(
            "/api/v1/eligibility",
            json={"user_id": "u1001", "query": "am i eligible for lottery?"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "u1001"
    assert body["response"] == "Yes, you are eligible."


def test_api_eligibility_user_not_found(monkeypatch) -> None:
    monkeypatch.setattr(
        routes,
        "run_workflow",
        lambda state, db: {
            **state,
            "decision_reason": "user_not_found",
        },
    )
    app.dependency_overrides[routes.get_db] = lambda: object()
    try:
        response = client.post(
            "/api/v1/eligibility",
            json={"user_id": "missing", "query": "what is my balance?"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_api_eligibility_db_error(monkeypatch) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    def _raise_db_error(state, db):
        raise SQLAlchemyError("db down")

    monkeypatch.setattr(routes, "run_workflow", _raise_db_error)
    app.dependency_overrides[routes.get_db] = lambda: object()
    try:
        response = client.post(
            "/api/v1/eligibility",
            json={"user_id": "u1001", "query": "what is my balance?"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503


def test_api_pii_savings_eligibility_lottery(monkeypatch) -> None:
    def _detokenize(masked_query, db):
        if masked_query == "am i eligible <PII_TOKEN>?":
            return "am i eligible for the lottery?"
        return masked_query

    monkeypatch.setattr(
        routes,
        "detokenize_masked_query_from_vault",
        _detokenize,
    )
    monkeypatch.setattr(
        routes,
        "run_savings_agent",
        lambda state, db: {
            **state,
            "balance": 76000.0,
            "years_in_bank": 4,
            "decision_reason": "savings_loaded",
        },
    )
    monkeypatch.setattr(
        routes,
        "run_prize_money_agent",
        lambda state: {
            **state,
            "eligible": True,
            "decision_reason": "User meets both balance and tenure requirements.",
        },
    )
    monkeypatch.setattr(
        routes,
        "run_response_agent",
        lambda state: {**state, "final_response": "LLM masked response for eligibility."},
    )
    app.dependency_overrides[routes.get_db] = lambda: object()
    try:
        response = client.post(
            "/api/v1/agents/pii-savings-eligibility-response",
            json={"user_id": "u1001", "masked_query": "am i eligible <PII_TOKEN>?"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["remasked_query"] == "am i eligible <PII_TOKEN>?"
    assert body["unmasked_query"] == "am i eligible for the lottery?"
    assert body["balance"] == 76000.0
    assert body["years_in_bank"] == 4
    assert body["eligible"] is True
    assert body["actual_query_output"] == "LLM masked response for eligibility."
    assert body["user_query_output"] == "LLM masked response for eligibility."


def test_api_pii_savings_eligibility_balance(monkeypatch) -> None:
    def _detokenize(masked_query, db):
        if masked_query == "what is my <PII_X>?":
            return "what is my balance?"
        return masked_query

    monkeypatch.setattr(
        routes,
        "detokenize_masked_query_from_vault",
        _detokenize,
    )
    monkeypatch.setattr(
        routes,
        "run_savings_agent",
        lambda state, db: {
            **state,
            "balance": 49000.0,
            "years_in_bank": 5,
            "decision_reason": "savings_loaded",
        },
    )
    monkeypatch.setattr(
        routes,
        "run_response_agent",
        lambda state: {**state, "final_response": "LLM masked response for balance."},
    )
    app.dependency_overrides[routes.get_db] = lambda: object()
    try:
        response = client.post(
            "/api/v1/agents/pii-savings-eligibility-response",
            json={"user_id": "u1002", "masked_query": "what is my <PII_X>?"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["remasked_query"] == "what is my <PII_X>?"
    assert body["unmasked_query"] == "what is my balance?"
    assert body["balance"] == 49000.0
    assert body["years_in_bank"] == 5
    assert body["actual_query_output"] == "LLM masked response for balance."
    assert body["eligible"] is None
    assert body["user_query_output"] == "LLM masked response for balance."


def test_api_final_of_final(monkeypatch) -> None:
    monkeypatch.setattr(
        routes,
        "final_security_and_pii",
        lambda payload, db: routes.FinalSecurityPIIResponse(
            user_id=payload.user_id,
            input_query=payload.query,
            security_output="yes",
            security_reason="self query",
            security_flag="no warning",
            masked_query="am i eligible for <PII_TOKEN>?",
            masked_items=[routes.PIIMaskedItem(token="PII_TOKEN", pii_type="name")],
        ),
    )
    monkeypatch.setattr(
        routes,
        "pii_savings_eligibility_response",
        lambda payload, db: routes.PIISavingsEligibilityResponse(
            remasked_query=payload.masked_query,
            unmasked_query="am i eligible for lottery?",
            balance=76000.0,
            years_in_bank=4,
            eligible=True,
            actual_query_output="Masked response",
            user_query_output="Unmasked response",
        ),
    )
    app.dependency_overrides[routes.get_db] = lambda: object()
    try:
        response = client.post(
            "/api/v1/final-of-final",
            json={"user_id": "u1001", "query": "am i eligible for lottery?"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "u1001"
    assert body["security_output"] == "yes"
    assert body["eligible"] is True
    assert body["actual_query_output"] == "Masked response"
    assert body["user_query_output"] == "Unmasked response"
