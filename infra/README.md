Local Dev with Docker Compose
=============================

Prereqs: Docker, Docker Compose.

Steps:
1. Copy `.env.example` to `.env` (fill API keys if available).
2. From `infra/`, run: `docker compose up --build`.
3. Frontend: http://localhost:3000
4. Backend: http://localhost:8000
5. MinIO Console: http://localhost:9001 (minioadmin/minioadmin)

Services:
- postgres, redis, minio, chroma
- backend (FastAPI), worker (Celery), poller (metrics), frontend (Next.js)


