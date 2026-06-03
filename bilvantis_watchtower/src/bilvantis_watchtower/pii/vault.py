from dataclasses import dataclass
from datetime import datetime
import re
from uuid import uuid4

from sqlalchemy import BigInteger, Integer, String, TEXT, TIMESTAMP, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class VaultBase(DeclarativeBase):
    pass


class PIITokenVault(VaultBase):
    __tablename__ = "pii_token_vault"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    pii_type: Mapped[str] = mapped_column(String(64), nullable=False)
    pii_value: Mapped[str] = mapped_column(TEXT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


@dataclass
class PIIMaskedItem:
    token: str
    pii_type: str


@dataclass
class PIIMaskResult:
    masked_query: str
    masked_items: list[PIIMaskedItem]


TOKEN_PATTERN = re.compile(r"<(PII_[A-Z0-9_]+)>")


def store_pii_entities_in_vault(
    masked_query: str,
    pii_entities: list[dict[str, str]],
    db: Session,
    token_model: type[PIITokenVault] = PIITokenVault,
) -> PIIMaskResult:
    updated_query = masked_query
    masked_items: list[PIIMaskedItem] = []

    for index, pii in enumerate(pii_entities, start=1):
        value = pii["value"]
        pii_type = pii["pii_type"]
        token = f"PII_{uuid4().hex[:12].upper()}"
        placeholder = f"<PII_{index}>"
        updated_query = updated_query.replace(placeholder, f"<{token}>")
        db.add(token_model(token=token, pii_type=pii_type, pii_value=value))
        masked_items.append(PIIMaskedItem(token=token, pii_type=pii_type))

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return PIIMaskResult(masked_query=updated_query, masked_items=masked_items)


def detokenize_masked_query_from_vault(
    masked_query: str,
    db: Session,
    token_model: type[PIITokenVault] = PIITokenVault,
) -> str:
    tokens = sorted(set(TOKEN_PATTERN.findall(masked_query)))
    if not tokens:
        return masked_query

    value_by_token = _load_token_values(tokens, db, token_model)
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


def detokenize_text_from_vault(
    text: str,
    db: Session,
    strict: bool = False,
    token_model: type[PIITokenVault] = PIITokenVault,
) -> str:
    tokens = sorted(set(TOKEN_PATTERN.findall(text)))
    if not tokens:
        return text

    value_by_token = _load_token_values(tokens, db, token_model)
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
    token_model: type[PIITokenVault] = PIITokenVault,
) -> str:
    tokens = sorted(set(TOKEN_PATTERN.findall(tokenized_query)))
    if not tokens:
        return unmasked_query

    value_by_token = _load_token_values(tokens, db, token_model)
    missing_tokens = [token for token in tokens if token not in value_by_token]
    if missing_tokens:
        raise ValueError(f"Unknown PII tokens: {', '.join(missing_tokens)}")

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


def _load_token_values(
    tokens: list[str],
    db: Session,
    token_model: type[PIITokenVault],
) -> dict[str, str]:
    rows = db.query(token_model).filter(token_model.token.in_(tokens)).all()
    return {row.token: row.pii_value for row in rows}
