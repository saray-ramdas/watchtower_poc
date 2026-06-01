from bilvantis_watchtower.types import PIIDetectedEntity


def redact_query_with_tokens(
    query: str,
    pii_entities: list[PIIDetectedEntity],
) -> tuple[str, list[PIIDetectedEntity]]:
    masked_query = query
    applied_entities: list[PIIDetectedEntity] = []

    for entity in sorted(pii_entities, key=lambda x: len(x["value"]), reverse=True):
        value = entity["value"]
        pii_type = entity["pii_type"]
        if value not in masked_query:
            continue
        token = f"<PII_{len(applied_entities) + 1}>"
        masked_query = masked_query.replace(value, token)
        applied_entities.append({"value": value, "pii_type": pii_type})

    return masked_query, applied_entities
