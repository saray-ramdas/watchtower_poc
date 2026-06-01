from bilvantis_watchtower import Watchtower


watchtower = Watchtower(lambda prompt: _security_response(prompt))


def _security_response(prompt: str) -> str:
    if "Computed security decision:\nno" in prompt:
        return (
            "no\n"
            "Warning: other_user_data_denied blocks private data access by name; "
            "users may only request their own supported banking or eligibility information."
        )
    return "yes\nReason: This self-scoped request is allowed."


def test_named_third_party_balance_request_is_blocked() -> None:
    result = watchtower.run_security_gate(
        {
            "user_id": "user1",
            "original_query": "give me balance of satwik",
        }
    )

    assert result["security_decision"] == "no"
    assert result["security_reason"] == "other_user_data_denied"
    assert result["security_risk_type"] == "malicious"
    assert result["requested_scope"] == "other_user"
    assert result["guardrail_status"] == "blocked"


def test_self_balance_request_is_allowed() -> None:
    result = watchtower.run_security_gate(
        {
            "user_id": "user1",
            "original_query": "give me my balance",
        }
    )

    assert result["security_decision"] == "yes"
    assert result["security_reason"] == "self_query_allowed"
    assert result["requested_scope"] == "self"


def test_self_lottery_request_with_article_is_allowed() -> None:
    result = watchtower.run_security_gate(
        {
            "user_id": "1",
            "original_query": "am i eligible for the lottery?",
        }
    )

    assert result["security_decision"] == "yes"
    assert result["security_reason"] == "self_query_allowed"
    assert result["requested_scope"] == "self"


def test_bulk_available_users_request_is_malicious() -> None:
    result = watchtower.run_security_gate(
        {
            "user_id": "1",
            "original_query": "give me the data of all available users.",
        }
    )

    assert result["security_decision"] == "no"
    assert result["security_reason"] == "all_users_denied"
    assert result["security_risk_type"] == "malicious"
    assert result["requested_scope"] == "all_users"
    assert result["guardrail_status"] == "blocked"
