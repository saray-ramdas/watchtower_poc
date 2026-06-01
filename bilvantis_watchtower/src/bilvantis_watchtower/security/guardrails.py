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
PRIVATE_SUBJECT_AFTER_PATTERN = re.compile(
    r"\b(?:bank\s+)?(?:account\s+)?(?:balance|savings|tenure|eligibility|lottery|prize)"
    r"\s+(?:of|for|about)\s+([a-z][\w-]*)\b",
    re.IGNORECASE,
)
PRIVATE_SUBJECT_BEFORE_PATTERN = re.compile(
    r"\b([a-z][\w-]*)'?s\s+(?:bank\s+)?(?:account\s+)?"
    r"(?:balance|savings|tenure|eligibility|lottery|prize)\b",
    re.IGNORECASE,
)
PRIVATE_SUBJECT_DIRECT_PATTERN = re.compile(
    r"\b(?:of|for|about)\s+([a-z][\w-]*)\s+(?:bank\s+)?(?:account\s+)?"
    r"(?:balance|savings|tenure|eligibility|lottery|prize)\b",
    re.IGNORECASE,
)
SELF_REFERENCES = {
    "i",
    "me",
    "my",
    "mine",
    "myself",
}
NON_SUBJECT_TOKENS = {
    "a",
    "an",
    "the",
    "any",
    "all",
    "this",
    "that",
    "these",
    "those",
    "lottery",
    "prize",
    "balance",
    "savings",
    "tenure",
    "eligibility",
}


def contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def normalize_query(query: str) -> str:
    return f" {query.lower().strip()} "


def extract_mentioned_user_ids(query: str) -> list[str]:
    return sorted({match.group(0).lower() for match in USER_ID_PATTERN.finditer(query)})


def extract_private_subject_refs(query: str) -> list[str]:
    refs = set()
    for pattern in (
        PRIVATE_SUBJECT_AFTER_PATTERN,
        PRIVATE_SUBJECT_BEFORE_PATTERN,
        PRIVATE_SUBJECT_DIRECT_PATTERN,
    ):
        refs.update(match.group(1).lower() for match in pattern.finditer(query))
    return sorted(
        ref for ref in refs if ref not in SELF_REFERENCES and ref not in NON_SUBJECT_TOKENS
    )


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
    private_subject_refs = extract_private_subject_refs(normalized_query)

    if contains_any(normalized_query, BULK_DATA_TERMS):
        return "all_users"

    if private_subject_refs:
        if all(
            ref in SELF_REFERENCES or ref == normalized_user_id
            for ref in private_subject_refs
        ):
            return "self"
        return "other_user"

    if mentioned_user_ids:
        if all(user_id == normalized_user_id for user_id in mentioned_user_ids):
            return "self"
        return "other_user"

    if contains_any(normalized_query, THIRD_PERSON_TERMS):
        return "unknown"

    if contains_any(normalized_query, SELF_TERMS):
        return "self"

    return "unknown"
