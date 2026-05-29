import re


BLOCKED_TERMS = (
    "ignore previous",
    "ignore instructions",
    "system prompt",
    "developer message",
    "drop table",
    "delete from",
    "password",
    "secret",
    "ssn",
    "social security",
    "credential",
    "api key",
)

BULK_DATA_TERMS = (
    "all users",
    "all user",
    "all customers",
    "all customer",
    "everyone",
    "every user",
    "every customer",
    "list of users",
    "list users",
    "customer list",
    "entire data",
    "entire database",
    "full database",
    "full customer",
    "all records",
    "show table",
    "dump",
    "export",
)

SELF_TERMS = (
    " i ",
    " me ",
    " my ",
    " mine ",
    " myself ",
    " am i ",
    " do i ",
    " have i ",
)

THIRD_PERSON_TERMS = (
    " his ",
    " her ",
    " their ",
    " another user",
    " other user",
    " someone else",
    " other customer",
    " another customer",
)

USER_ID_PATTERN = re.compile(r"\buser[\w-]*\b", re.IGNORECASE)


def contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def normalize_query(query: str) -> str:
    return f" {query.lower().strip()} "


def extract_mentioned_user_ids(query: str) -> list[str]:
    return sorted({match.group(0).lower() for match in USER_ID_PATTERN.finditer(query)})


def classify_intent(normalized_query: str) -> str:
    balance_terms = ("balance", "savings", "account amount", "how much money")
    tenure_terms = ("years", "tenure", "how long", "with the bank")
    lottery_terms = ("lottery", "eligible", "eligibility", "qualify", "qualified", "prize")

    if contains_any(normalized_query, lottery_terms):
        return "lottery_eligibility"
    if contains_any(normalized_query, balance_terms):
        return "bank_balance"
    if contains_any(normalized_query, tenure_terms):
        return "bank_tenure"
    return "unsupported"


def classify_scope(
    normalized_query: str,
    authenticated_user_id: str,
    mentioned_user_ids: list[str],
) -> str:
    normalized_user_id = authenticated_user_id.lower().strip()

    if contains_any(normalized_query, BULK_DATA_TERMS):
        return "all_users"

    if mentioned_user_ids:
        if all(user_id == normalized_user_id for user_id in mentioned_user_ids):
            return "self"
        return "other_user"

    if contains_any(normalized_query, THIRD_PERSON_TERMS):
        return "unknown"

    if contains_any(normalized_query, SELF_TERMS):
        return "self"

    return "unknown"
