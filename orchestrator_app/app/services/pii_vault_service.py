from sqlalchemy.orm import Session

from bilvantis_watchtower import (
    PIIMaskedItem,
    PIIMaskResult,
    detokenize_masked_query_from_vault as sdk_detokenize_masked_query_from_vault,
    detokenize_text_from_vault as sdk_detokenize_text_from_vault,
    remask_query_with_existing_tokens as sdk_remask_query_with_existing_tokens,
    store_pii_entities_in_vault as sdk_store_pii_entities_in_vault,
)

from ..db.models import PIITokenVault


def store_pii_entities_in_vault(
    masked_query: str,
    pii_entities: list[dict[str, str]],
    db: Session,
) -> PIIMaskResult:
    return sdk_store_pii_entities_in_vault(
        masked_query=masked_query,
        pii_entities=pii_entities,
        db=db,
        token_model=PIITokenVault,
    )


def detokenize_masked_query_from_vault(masked_query: str, db: Session) -> str:
    return sdk_detokenize_masked_query_from_vault(
        masked_query=masked_query,
        db=db,
        token_model=PIITokenVault,
    )


def detokenize_text_from_vault(text: str, db: Session, strict: bool = False) -> str:
    return sdk_detokenize_text_from_vault(
        text=text,
        db=db,
        strict=strict,
        token_model=PIITokenVault,
    )


def remask_query_with_existing_tokens(
    unmasked_query: str,
    tokenized_query: str,
    db: Session,
) -> str:
    return sdk_remask_query_with_existing_tokens(
        unmasked_query=unmasked_query,
        tokenized_query=tokenized_query,
        db=db,
        token_model=PIITokenVault,
    )


__all__ = [
    "PIIMaskedItem",
    "PIIMaskResult",
    "detokenize_masked_query_from_vault",
    "detokenize_text_from_vault",
    "remask_query_with_existing_tokens",
    "store_pii_entities_in_vault",
]
