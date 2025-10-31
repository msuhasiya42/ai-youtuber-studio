from celery_worker import app
from app.services.llm_provider import get_provider


@app.task
def embed_texts(texts: list[str]) -> list[list[float]]:
    provider = get_provider()
    return provider.embed(texts)


