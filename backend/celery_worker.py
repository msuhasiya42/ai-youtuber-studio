from celery import Celery
import os

broker_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
backend_url = broker_url

app = Celery("ai_youtuber_studio", broker=broker_url, backend=backend_url)
app.conf.update(
    task_routes={
        "app.services.ingest_worker.*": {"queue": "ingest"},
        "app.services.transcribe_worker.*": {"queue": "transcribe"},
        "app.services.embedding_worker.*": {"queue": "embedding"},
        "app.services.generation_worker.*": {"queue": "generation"},
        "app.services.insights_worker.*": {"queue": "insights"},
    },
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Tasks will be auto-discovered when Celery worker starts
# Do not import task modules here to avoid circular imports with FastAPI


