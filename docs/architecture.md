Overview
========

Components:
- FastAPI backend (`backend/app`) with REST and WebSocket.
- Celery workers using Redis broker for ingest/transcribe/embed/generate/insights.
- PostgreSQL via SQLAlchemy ORM.
- MinIO (S3-compatible) for audio/transcripts storage.
- ChromaDB for vector search (stub hookup).
- Next.js frontend (`frontend`) for UI, live updates via WebSocket.

Live Updates Flow:
- Poller publishes metrics to Redis pub/sub `metrics_updates` channel.
- FastAPI `/ws` relays messages to clients.

LLM Provider Layer:
- `LLMProvider` abstract class with `GeminiProvider` and `OpenAIProvider` implementations.
- `LLM_PROVIDER` env chooses provider.

Security:
- Env-configured CORS.
- Rate limiting via `slowapi` (to be integrated per-route as needed).
- Encryption key placeholder for token encryption.


