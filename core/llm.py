import json
import requests

from config import GROQ_API_KEY, GROQ_BASE_URL

HTTP = requests.Session()


class LLMError(RuntimeError):
    pass


def _post(payload, timeout):
    if not GROQ_API_KEY:
        raise LLMError("GROQ_API_KEY chưa được cấu hình.")

    try:
        response = HTTP.post(
            GROQ_BASE_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
    except requests.Timeout as exc:
        raise LLMError(f"Groq timeout after {timeout}s") from exc
    except requests.RequestException as exc:
        raise LLMError(f"Groq request error: {type(exc).__name__}") from exc

    if response.status_code >= 400:
        raise LLMError(f"Groq HTTP {response.status_code}: {response.text[:350]}")

    return response


def chat_structured(model, messages, schema_name, schema, reasoning_effort="low",
                    timeout=10, temperature=0.2, max_completion_tokens=1000):
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_completion_tokens": max_completion_tokens,
        "reasoning_effort": reasoning_effort,
        "reasoning_format": "hidden",
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": schema},
        },
    }
    response = _post(payload, timeout)
    try:
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as exc:
        raise LLMError(f"Không đọc được structured output: {type(exc).__name__}") from exc


def chat_text(model, messages, reasoning_effort="low", timeout=1.6,
              temperature=0.12, max_completion_tokens=280):
    """Fast path cho Zalo Dynamic: một lần gọi model, không JSON schema."""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_completion_tokens": max_completion_tokens,
        "reasoning_effort": reasoning_effort,
        "reasoning_format": "hidden",
    }
    response = _post(payload, timeout)
    try:
        return str(response.json()["choices"][0]["message"]["content"] or "").strip()
    except Exception as exc:
        raise LLMError(f"Không đọc được text output: {type(exc).__name__}") from exc
