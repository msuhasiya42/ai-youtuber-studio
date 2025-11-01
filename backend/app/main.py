from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
import os
import asyncio
import redis
import time
from app.api import auth, channels, videos, insights, transcripts, content_studio
from app.core.logging_config import setup_logging, get_logger, set_request_id, clear_request_id

# Initialize logging
setup_logging()
logger = get_logger(__name__)

app = FastAPI(default_response_class=ORJSONResponse, title="AI YouTuber Studio")

logger.info("FastAPI application initialized")


# Request/Response Logging Middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses"""

    async def dispatch(self, request: Request, call_next):
        # Generate and set request ID
        request_id = set_request_id()

        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"[client:{request.client.host if request.client else 'unknown'}] "
            f"[user-agent:{request.headers.get('user-agent', 'unknown')[:50]}]"
        )

        # Track timing
        start_time = time.time()

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            log_level = logger.info if response.status_code < 400 else logger.error
            log_level(
                f"Response: {request.method} {request.url.path} "
                f"[status:{response.status_code}] "
                f"[duration:{duration_ms:.2f}ms]"
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"[duration:{duration_ms:.2f}ms] [error:{str(e)}]",
                exc_info=True
            )
            raise
        finally:
            # Clean up request context
            clear_request_id()


# Add middleware
app.add_middleware(LoggingMiddleware)

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
app.include_router(transcripts.router, prefix="/api/transcripts", tags=["transcripts"])
app.include_router(content_studio.router, prefix="/api/content-studio", tags=["content-studio"])

logger.info("All API routers registered")

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
logger.info(f"Redis client initialized: {redis_url}")


# Application lifecycle events
@app.on_event("startup")
async def startup_event():
    """Log application startup"""
    logger.info("=" * 80)
    logger.info("AI YouTuber Studio Backend - Starting Up")
    logger.info(f"Environment: {os.getenv('ENV', 'development')}")
    logger.info(f"CORS Origins: {origins}")
    logger.info("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown"""
    logger.info("=" * 80)
    logger.info("AI YouTuber Studio Backend - Shutting Down")
    logger.info("=" * 80)


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


