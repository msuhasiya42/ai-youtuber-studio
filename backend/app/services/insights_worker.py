from celery_worker import app as celery_app
from app.services.llm_provider import get_provider


@celery_app.task
def generate_top_performer_insights(context: str) -> dict:
    provider = get_provider()
    prompt = (
        "Analyze why these videos performed well:\n"
        "- Use title, transcript, comments, and metrics\n"
        "- Return key drivers, replicable patterns, and suggestions\n"
        "Output JSON only: { \"drivers\": [], \"patterns\": [], \"suggestions\": [] }\n\n"
        f"Context: {context}"
    )
    text = provider.generate(prompt)
    return {"raw": text}


