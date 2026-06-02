from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from bilvantis_watchtower import (
    VaultBase,
    detokenize_masked_query_from_vault,
    detokenize_text_from_vault,
    remask_query_with_existing_tokens,
    store_pii_entities_in_vault,
)


def test_store_detokenize_and_remask_pii_vault() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    VaultBase.metadata.create_all(bind=engine)

    with Session(engine) as db:
        result = store_pii_entities_in_vault(
            masked_query="my email is <PII_1>",
            pii_entities=[{"value": "ameya@test.com", "pii_type": "EMAIL"}],
            db=db,
        )

        assert result.masked_items[0].pii_type == "EMAIL"
        token = result.masked_items[0].token
        assert result.masked_query == f"my email is <{token}>"

        assert (
            detokenize_masked_query_from_vault(result.masked_query, db)
            == "my email is ameya@test.com"
        )
        assert (
            detokenize_text_from_vault(f"contact <{token}>", db)
            == "contact ameya@test.com"
        )
        assert (
            remask_query_with_existing_tokens(
                "my email is ameya@test.com",
                result.masked_query,
                db,
            )
            == result.masked_query
        )
