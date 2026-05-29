import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv


ROOT_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=ROOT_ENV_PATH, override=False)


class LLMGenerationError(RuntimeError):
    pass


def is_llm_configured() -> bool:
    return bool(os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_URL"))


def generate_llm_response(prompt: str) -> str | None:
    if os.getenv("GROQ_API_KEY"):
        return _generate_with_groq(prompt)

    if os.getenv("LLM_API_URL"):
        return _generate_with_generic_endpoint(prompt)

    return None


def _post_json(url: str, payload: dict, headers: dict, timeout: int = 30) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise LLMGenerationError(
            f"LLM provider returned HTTP {exc.code}: {detail}"
        ) from exc
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise LLMGenerationError(f"LLM provider request failed: {exc}") from exc


def _extract_chat_content(body: dict) -> str:
    try:
        generated = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMGenerationError("LLM provider response did not include chat content") from exc

    if not isinstance(generated, str) or not generated.strip():
        raise LLMGenerationError("LLM provider returned an empty response")

    return generated.strip()


def _generate_with_groq(prompt: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise LLMGenerationError("GROQ_API_KEY is not configured")

    payload = {
        "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a banking response agent. Follow the provided guardrails, "
                    "answer only from supplied context, and return only the final "
                    "customer-facing response."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "500")),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "watchtower-poc/1.0",
    }
    body = _post_json(
        os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions"),
        payload,
        headers,
    )
    return _extract_chat_content(body)


def _generate_with_generic_endpoint(prompt: str) -> str:
    api_url = os.getenv("LLM_API_URL")
    if not api_url:
        raise LLMGenerationError("LLM_API_URL is not configured")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "watchtower-poc/1.0",
    }
    api_key = os.getenv("LLM_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    body = _post_json(api_url, {"prompt": prompt}, headers)
    generated = body.get("response") or body.get("text")

    if not isinstance(generated, str) or not generated.strip():
        raise LLMGenerationError("Generic LLM endpoint returned an empty response")

    return generated.strip()
