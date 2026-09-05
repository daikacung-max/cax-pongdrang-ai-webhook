import requests

from core.providers.base import ChatProvider, ProviderError, ProviderTimeout


class OpenAICompatibleProvider(ChatProvider):
    def __init__(self, name, api_key, base_url):
        self.name = name
        self.api_key = str(api_key or "").strip()
        self.base_url = str(base_url or "").strip()
        self.http = requests.Session()

    def complete(self, payload, timeout):
        if not self.api_key:
            raise ProviderError(f"{self.name} API key chưa được cấu hình.")
        try:
            response = self.http.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout,
            )
        except requests.Timeout as exc:
            raise ProviderTimeout(f"{self.name} timeout after {timeout}s") from exc
        except requests.RequestException as exc:
            raise ProviderError(f"{self.name} request error: {type(exc).__name__}") from exc

        if response.status_code >= 400:
            # Không đưa response body vào lỗi/log vì provider có thể phản chiếu input.
            raise ProviderError(f"{self.name} HTTP {response.status_code}")
        return response
