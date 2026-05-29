import sys
from pathlib import Path


SDK_SRC = Path(__file__).resolve().parents[1] / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from bilvantis_watchtower.security import run_security_gate


def _security_response(prompt: str) -> str:
    if "Computed security decision:\nno" in prompt:
        return (
            "no\n"
            "Warning: other_user_data_denied blocks private data access by name; "
            "users may only request their own supported banking or eligibility information."
        )
    return "yes\nReason: This self-scoped request is allowed."


def test_named_third_party_balance_request_is_blocked() -> None:
    result = run_security_gate(
        {
            "user_id": "user1",
            "original_query": "give me balance of satwik",
        },
        _security_response,
    )

    assert result["security_decision"] == "no"
    assert result["security_reason"] == "other_user_data_denied"
    assert result["security_risk_type"] == "malicious"
    assert result["requested_scope"] == "other_user"
    assert result["guardrail_status"] == "blocked"


def test_self_balance_request_is_allowed() -> None:
    result = run_security_gate(
        {
            "user_id": "user1",
            "original_query": "give me my balance",
        },
        _security_response,
    )

    assert result["security_decision"] == "yes"
    assert result["security_reason"] == "self_query_allowed"
    assert result["requested_scope"] == "self"
