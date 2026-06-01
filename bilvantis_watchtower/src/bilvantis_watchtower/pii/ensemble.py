import json
import re

from bilvantis_watchtower.exceptions import PIIDetectionError
from bilvantis_watchtower.types import PIIDetectedEntity, SecurityLLMGenerator


def build_pii_detection_prompt(query: str) -> str:
    return (
        "You are a strict PII extraction engine.\n"
        "Identify personal/sensitive information in the user query.\n"
        "Return ONLY valid JSON in this format:\n"
        '{"pii":[{"value":"<exact substring from query>","type":"<PII type>"}]}\n'
        "Rules:\n"
        "1) value must be exact text copied from query.\n"
        "2) Include names, emails, phone numbers, addresses, account/card/ID numbers, DOB, passport, national IDs.\n"
        "3) If none exists return {\"pii\":[]}.\n"
        f"Query: {query}"
    )


def _extract_json_payload(raw_output: str) -> dict:
    text = raw_output.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def detect_pii_entities(query: str, generate_llm_response: SecurityLLMGenerator) -> list[PIIDetectedEntity]:
    generated = generate_llm_response(build_pii_detection_prompt(query))
    if not generated:
        raise PIIDetectionError("LLM did not return PII output")

    try:
        payload = _extract_json_payload(generated)
    except json.JSONDecodeError as exc:
        raise PIIDetectionError("LLM returned non-JSON output for PII detection") from exc

    items = payload.get("pii", [])
    if not isinstance(items, list):
        raise PIIDetectionError("LLM JSON does not contain a valid 'pii' list")

    normalized: list[PIIDetectedEntity] = []
    seen_values: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        value = str(item.get("value", "")).strip()
        pii_type = str(item.get("type", "")).strip() or "UNKNOWN"
        if not value or value in seen_values:
            continue
        seen_values.add(value)
        normalized.append({"value": value, "pii_type": pii_type.upper()})
    return normalized
