Runbook
=======

Local Development
-----------------
1. Copy `.env.example` to `.env` and fill keys if available.
2. From `infra/`, run `docker compose up --build`.
3. Access:
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000/docs
   - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)

Processes
---------
- Backend API (`uvicorn`) serves REST and WebSocket `/ws`.
- Celery worker processes queues: ingest, transcribe, embedding, generation, insights.
- Metrics poller publishes updates to Redis `metrics_updates`, forwarded to clients by `/ws`.

Common Commands
---------------
- Rebuild: `docker compose build` (run from `infra/`).
- View logs: `docker compose logs -f backend worker poller`.
- DB shell: `docker exec -it $(docker ps -qf name=postgres) psql -U user -d youtubestudio`.

Troubleshooting
---------------
- If frontend fails to fetch: ensure `NEXT_PUBLIC_BACKEND_URL` points to backend URL.
- If WebSocket not connecting: check `NEXT_PUBLIC_WS_URL` and backend `/ws` route.
- If MinIO bucket missing: container `createbuckets` should create `youtube-data`. Restart infra if needed.


