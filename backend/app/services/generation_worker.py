from celery_worker import app
from app.services.llm_provider import get_provider


@app.task
def generate_summary_and_ideas(transcript_excerpt: str) -> dict:
    provider = get_provider()
    prompt = (
        "You are an expert YouTube strategist. Given transcript excerpts and metadata,\n"
        "return: 1) summary (3 sentences) 2) 3 creative video ideas relevant to the channel style\n"
        "3) a script outline for the top idea (Hook → Intro → Body → CTA)\n"
        "Output JSON only: { \"summary\": \"\", \"ideas\": [], \"outline\": \"\" }\n\n"
        f"Transcript: {transcript_excerpt}"
    )
    text = provider.generate(prompt)
    return {"raw": text}


@app.task
def generate_script(outline: str, tone: str | None = None, minutes: int | None = 8) -> str:
    provider = get_provider()
    prompt = (
        f"Write a full YouTube script (~{minutes} minutes) with tone: {tone or 'default'}.\n"
        f"Use this outline: {outline}"
    )
    return provider.generate(prompt)


