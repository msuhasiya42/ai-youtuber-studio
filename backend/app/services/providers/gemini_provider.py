import os
import google.generativeai as genai
from app.services.llm_provider import LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash") if api_key else None

    def embed(self, texts: list[str]) -> list[list[float]]:
        # Minimal mock embeddings if not configured
        if not self.model:
            return [[0.0 for _ in range(8)] for _ in texts]
        # Placeholder: use simple text lengths as embeddings to avoid heavy API calls here
        return [[float(len(t))] * 8 for t in texts]

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.model:
            return "Mock generation result."
        resp = self.model.generate_content(prompt)
        return resp.text or ""

    def chat(self, messages: list[dict], **kwargs) -> dict:
        # Simple single-shot emulate
        content = "\n".join([m.get("content", "") for m in messages])
        return {"content": self.generate(content)}


