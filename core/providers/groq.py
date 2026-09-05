from config import GROQ_API_KEY, GROQ_BASE_URL
from core.providers.http import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    def __init__(self):
        super().__init__("groq", GROQ_API_KEY, GROQ_BASE_URL)
