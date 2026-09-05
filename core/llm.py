import json

from core.providers import provider_for_model, provider_name_for_model
from core.providers.base import ProviderError, ProviderTimeout


class LLMError(RuntimeError):
    pass


class LLMTimeout(LLMError):
    pass


def _is_gpt56(model):
    return str(model or "").startswith("gpt-5.6")


def _post(model, payload, timeout, safety_identifier=None):
    provider_name = provider_name_for_model(model)
    if provider_name == "openai" and safety_identifier:
        payload["safety_identifier"] = str(safety_identifier)[:64]
    try:
        return provider_for_model(model).complete(payload, timeout)
    except ProviderTimeout as exc:
        raise LLMTimeout(str(exc)) from exc
    except ProviderError as exc:
        raise LLMError(str(exc)) from exc


def chat_structured(model, messages, schema_name, schema, reasoning_effort="low",
                    timeout=10, temperature=0.2, max_completion_tokens=1000,
                    safety_identifier=None):
    payload = {
        "model": model,
        "messages": messages,
        "max_completion_tokens": max_completion_tokens,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": schema},
        },
    }
    if _is_gpt56(model):
        payload["reasoning_effort"] = reasoning_effort
    else:
        payload["temperature"] = temperature
    if str(model).startswith("openai/gpt-oss"):
        payload["reasoning_effort"] = reasoning_effort
        payload["reasoning_format"] = "hidden"

    response = _post(model, payload, timeout, safety_identifier=safety_identifier)
    try:
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as exc:
        raise LLMError(f"Không đọc được structured output: {type(exc).__name__}") from exc


def chat_text(model, messages, reasoning_effort="low", timeout=1.6,
              temperature=0.12, max_completion_tokens=280,
              safety_identifier=None):
    """Một lần gọi model cho Zalo Dynamic, không dùng JSON schema."""
    payload = {
        "model": model,
        "messages": messages,
        "max_completion_tokens": max_completion_tokens,
    }
    if _is_gpt56(model):
        payload["reasoning_effort"] = reasoning_effort
    else:
        payload["temperature"] = temperature
    if str(model).startswith("openai/gpt-oss"):
        payload["reasoning_effort"] = reasoning_effort
        payload["reasoning_format"] = "hidden"

    response = _post(model, payload, timeout, safety_identifier=safety_identifier)
    try:
        return str(response.json()["choices"][0]["message"]["content"] or "").strip()
    except Exception as exc:
        raise LLMError(f"Không đọc được text output: {type(exc).__name__}") from exc
