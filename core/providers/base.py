from abc import ABC, abstractmethod


class ProviderError(RuntimeError):
    pass


class ProviderTimeout(ProviderError):
    pass


class ChatProvider(ABC):
    name = "unknown"

    @abstractmethod
    def complete(self, payload, timeout):
        raise NotImplementedError
