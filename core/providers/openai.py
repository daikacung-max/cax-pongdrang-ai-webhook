from config import OPENAI_API_KEY, OPENAI_BASE_URL
from core.providers.http import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    def __init__(self):
        super().__init__("openai", OPENAI_API_KEY, OPENAI_BASE_URL)
