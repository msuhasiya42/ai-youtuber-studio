from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
import os
import asyncio
import redis
from app.api import auth, channels, videos, insights


app = FastAPI(default_response_class=ORJSONResponse, title="AI YouTuber Studio")

origins = os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(channels.router, prefix="/api/channels", tags=["channels"])
app.include_router(videos.router, prefix="/api/videos", tags=["videos"])
app.include_router(insights.router, prefix="/api/insights", tags=["insights"])


redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = redis.Redis.from_url(redis_url, decode_responses=True)


@app.get("/")
async def root():
    return {"status": "ok", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    pubsub = redis_client.pubsub()
    pubsub.subscribe("metrics_updates")
    try:
        while True:
            message = pubsub.get_message(timeout=1.0)
            if message and message.get("type") == "message":
                await ws.send_text(message.get("data"))
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            pubsub.close()
        except Exception:
            pass


