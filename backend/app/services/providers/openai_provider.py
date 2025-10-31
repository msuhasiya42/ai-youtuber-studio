import os
from openai import OpenAI
from app.services.llm_provider import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.client:
            return [[0.0 for _ in range(8)] for _ in texts]
        # Placeholder: real implementation would call embeddings
        return [[float(len(t))] * 8 for t in texts]

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.client:
            return "Mock OpenAI generation."
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content

    def chat(self, messages: list[dict], **kwargs) -> dict:
        content = "\n".join([m.get("content", "") for m in messages])
        return {"content": self.generate(content)}


