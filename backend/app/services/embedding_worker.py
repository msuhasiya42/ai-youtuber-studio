from celery_worker import app as celery_app
from app.services.llm_provider import get_provider


@celery_app.task
def embed_texts(texts: list[str]) -> list[list[float]]:
    provider = get_provider()
    return provider.embed(texts)


