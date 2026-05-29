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
