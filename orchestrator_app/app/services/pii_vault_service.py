from dataclasses import dataclass
import re
from uuid import uuid4

from sqlalchemy.orm import Session

from ..db.models import PIITokenVault


@dataclass
class PIIMaskedItem:
    token: str
    pii_type: str


@dataclass
class PIIMaskResult:
    masked_query: str
    masked_items: list[PIIMaskedItem]


def store_pii_entities_in_vault(
    masked_query: str,
    pii_entities: list[dict[str, str]],
    db: Session,
) -> PIIMaskResult:
    updated_query = masked_query
    masked_items: list[PIIMaskedItem] = []

    for index, pii in enumerate(pii_entities, start=1):
        value = pii["value"]
        pii_type = pii["pii_type"]
        token = f"PII_{uuid4().hex[:12].upper()}"
        placeholder = f"<PII_{index}>"
        updated_query = updated_query.replace(placeholder, f"<{token}>")
        db.add(PIITokenVault(token=token, pii_type=pii_type, pii_value=value))
        masked_items.append(PIIMaskedItem(token=token, pii_type=pii_type))

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return PIIMaskResult(masked_query=updated_query, masked_items=masked_items)


TOKEN_PATTERN = re.compile(r"<(PII_[A-Z0-9_]+)>")


def detokenize_masked_query_from_vault(masked_query: str, db: Session) -> str:
    """
    Resolve <PII_...> tokens in a masked query using the token vault.
    Raises ValueError when one or more tokens are missing from the vault.
    """
    tokens = sorted(set(TOKEN_PATTERN.findall(masked_query)))
    if not tokens:
        return masked_query

    rows = db.query(PIITokenVault).filter(PIITokenVault.token.in_(tokens)).all()
    value_by_token = {row.token: row.pii_value for row in rows}
    missing_tokens = [token for token in tokens if token not in value_by_token]
    if missing_tokens:
        raise ValueError(f"Unknown PII tokens: {', '.join(missing_tokens)}")

    detokenized_query = masked_query
    for token in tokens:
        detokenized_query = detokenized_query.replace(
            f"<{token}>",
            value_by_token[token],
        )
    return detokenized_query


def detokenize_text_from_vault(text: str, db: Session, strict: bool = False) -> str:
    """
    Resolve all known <PII_...> tokens in any text.
    If strict=True, raise ValueError when any token is missing.
    """
    tokens = sorted(set(TOKEN_PATTERN.findall(text)))
    if not tokens:
        return text

    rows = db.query(PIITokenVault).filter(PIITokenVault.token.in_(tokens)).all()
    value_by_token = {row.token: row.pii_value for row in rows}
    missing_tokens = [token for token in tokens if token not in value_by_token]
    if strict and missing_tokens:
        raise ValueError(f"Unknown PII tokens: {', '.join(missing_tokens)}")

    detokenized = text
    for token, value in value_by_token.items():
        detokenized = detokenized.replace(f"<{token}>", value)
    return detokenized


def remask_query_with_existing_tokens(
    unmasked_query: str,
    tokenized_query: str,
    db: Session,
) -> str:
    """
    Re-mask an unmasked query using the same tokens already present in tokenized_query.
    """
    tokens = sorted(set(TOKEN_PATTERN.findall(tokenized_query)))
    if not tokens:
        return unmasked_query

    rows = db.query(PIITokenVault).filter(PIITokenVault.token.in_(tokens)).all()
    value_by_token = {row.token: row.pii_value for row in rows}
    missing_tokens = [token for token in tokens if token not in value_by_token]
    if missing_tokens:
        raise ValueError(f"Unknown PII tokens: {', '.join(missing_tokens)}")

    # Replace only in non-token text segments to avoid mutating existing token strings.
    spans = list(TOKEN_PATTERN.finditer(unmasked_query))
    if not spans:
        segments = [(unmasked_query, False)]
    else:
        segments: list[tuple[str, bool]] = []
        last = 0
        for match in spans:
            if match.start() > last:
                segments.append((unmasked_query[last:match.start()], False))
            segments.append((match.group(0), True))
            last = match.end()
        if last < len(unmasked_query):
            segments.append((unmasked_query[last:], False))

    replacement_pairs = sorted(
        ((value, f"<{token}>") for token, value in value_by_token.items()),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    remasked_parts: list[str] = []
    for segment_text, is_token_segment in segments:
        if is_token_segment:
            remasked_parts.append(segment_text)
            continue

        updated = segment_text
        for value, token_text in replacement_pairs:
            if value:
                updated = updated.replace(value, token_text)
        remasked_parts.append(updated)

    return "".join(remasked_parts)
