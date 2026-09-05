from functools import lru_cache

from core.providers.base import ProviderError


def provider_name_for_model(model):
    model = str(model or "").strip().lower()
    if model.startswith("openai/gpt-oss") or model.startswith("groq/"):
        return "groq"
    if model.startswith("gpt-5.6"):
        return "openai"
    raise ProviderError(f"Không có provider cho model: {model or 'empty'}")


@lru_cache(maxsize=2)
def _provider(name):
    if name == "groq":
        from core.providers.groq import GroqProvider
        return GroqProvider()
    if name == "openai":
        from core.providers.openai import OpenAIProvider
        return OpenAIProvider()
    raise ProviderError(f"Provider không được hỗ trợ: {name}")


def provider_for_model(model):
    return _provider(provider_name_for_model(model))
