import json
import requests

from config import GROQ_API_KEY, GROQ_BASE_URL

HTTP = requests.Session()


class LLMError(RuntimeError):
    pass


def chat_structured(model, messages, schema_name, schema, reasoning_effort="low",
                    timeout=10, temperature=0.2, max_completion_tokens=1000):
    if not GROQ_API_KEY:
        raise LLMError("GROQ_API_KEY chưa được cấu hình.")
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
    response = HTTP.post(
        GROQ_BASE_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )
    if response.status_code >= 400:
        raise LLMError(f"Groq HTTP {response.status_code}: {response.text[:500]}")
    try:
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as exc:
        raise LLMError(f"Không đọc được structured output: {exc}") from exc
