import os
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        ...

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:  # pragma: no cover
        ...

    @abstractmethod
    def chat(self, messages: list[dict], **kwargs) -> dict:  # pragma: no cover
        ...


def get_llm_provider() -> "LLMProvider":
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider == "openai":
        from app.services.providers.openai_provider import OpenAIProvider
        return OpenAIProvider()
    from app.services.providers.gemini_provider import GeminiProvider
    return GeminiProvider()


