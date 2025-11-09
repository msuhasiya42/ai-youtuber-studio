# Docker Worker Setup - Bug Fixes & Solutions

**Date:** November 9, 2025  
**Session:** Complete Docker Worker Configuration & Debugging

This document outlines all the issues encountered and resolved while setting up the Celery worker in Docker for the AI YouTuber Studio project.

---

## Table of Contents
1. [Redis Connection Issues](#1-redis-connection-issues)
2. [Worker Queue Configuration](#2-worker-queue-configuration)
3. [Docker Network Configuration](#3-docker-network-configuration)
4. [OAuth Scope Permissions](#4-oauth-scope-permissions)
5. [YouTubeClient Authentication Bug](#5-youtubeclient-authentication-bug)
6. [SRT Caption Parsing Error](#6-srt-caption-parsing-error)
7. [ChromaDB Version Mismatch](#7-chromadb-version-mismatch)
8. [YouTube API Quota](#8-youtube-api-quota)

---

## 1. Redis Connection Issues

### Problem
```
[ERROR] [celery.backends.redis] Connection to Redis lost: Retry (0/20) now.
```

FastAPI backend (running locally) was trying to connect to Redis using the Docker hostname `redis://redis:6379/0`, which only works inside Docker containers.

### Root Cause
- `.env` file had `REDIS_URL=redis://redis:6379/0`
- This URL only resolves inside Docker network
- Local processes need `localhost` instead

### Solution
Updated `.env` file:
```bash
# For local development (FastAPI running outside Docker)
REDIS_URL=redis://localhost:6379/0

# For Docker (worker running inside Docker)
# REDIS_URL=redis://redis:6379/0
```

### Files Changed
- `backend/.env`

---

## 2. Worker Queue Configuration

### Problem
- Worker was listening only to the `celery` queue
- Tasks were being routed to the `ingest` queue
- 20 tasks stuck in queue, never processed

### Root Cause
`celery_worker.py` configured task routing to `ingest` queue, but `docker-compose.yml` didn't specify queue names in the worker command, defaulting to only `celery` queue.

### Solution
Updated `docker-compose.yml` worker command:
```yaml
command: celery -A celery_worker worker --loglevel=info --concurrency=2 --max-tasks-per-child=50 --queues=ingest,transcribe,embedding,generation,insights,celery
```

### Verification
```bash
# Check queue lengths
redis-cli -h localhost -p 6379 LLEN ingest
redis-cli -h localhost -p 6379 LLEN celery
```

### Files Changed
- `backend/docker-compose.yml`

---

## 3. Docker Network Configuration

### Problem A: Redis Connection from Worker
```
ERROR: Cannot connect to redis://localhost:6379/0
Connection refused
```

Worker container was using `.env` value of `redis://localhost:6379/0` which doesn't work inside Docker.

### Solution A
Override `REDIS_URL` in `docker-compose.yml`:
```yaml
environment:
  - REDIS_URL=redis://redis:6379/0  # Force Docker hostname
```

### Problem B: PostgreSQL Connection from Worker
```
psycopg2.OperationalError: connection to server at "localhost" (::1), port 5432 failed
```

Worker needed to connect to local PostgreSQL (running on host machine).

### Solution B
Use `host.docker.internal` to access host services:
```yaml
environment:
  - DATABASE_URL=postgresql://mayur:jm145200@host.docker.internal:5432/aiyoutuberstudio
```

### Files Changed
- `backend/docker-compose.yml`

---

## 4. OAuth Scope Permissions

### Problem
```
403 Forbidden - "Request had insufficient authentication scopes"
```

The YouTube Captions API requires `youtube.force-ssl` scope, but the OAuth token was granted with only `youtube.readonly`.

### Root Cause
- `auth.py` had correct scopes including `youtube.force-ssl`
- `channels.py` and `ingest_worker.py` were using incomplete scope lists
- Existing refresh tokens didn't have the required scope

### Solution

**Step 1:** Updated scope lists in all files:
```python
scopes=[
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",  # Required for captions
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly"
]
```

**Step 2:** User had to re-authenticate to get new OAuth token with updated scopes.

### Files Changed
- `backend/app/api/channels.py` (2 locations)
- `backend/app/services/ingest_worker.py`

### Notes
- Existing refresh tokens cannot be "upgraded" with new scopes
- Users must disconnect and reconnect their YouTube account
- Alternative: Revoke access at https://myaccount.google.com/permissions

---

## 5. YouTubeClient Authentication Bug

### Problem
```python
TypeError: YouTubeClient.__init__() got an unexpected keyword argument 'user'
```

The `_fetch_authenticated_captions()` function was calling `YouTubeClient(user=video.channel.owner)` but the constructor only accepts `credentials`.

### Root Cause
Mismatch between function call and constructor signature:
```python
# Incorrect
youtube_client = YouTubeClient(user=video.channel.owner)

# YouTubeClient expects
def __init__(self, credentials: Optional[Credentials] = None):
```

### Solution
Updated `ingest_worker.py` to properly create credentials from user's refresh token:

```python
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest

def _fetch_authenticated_captions(video_id: str, video: Video) -> dict:
    user = video.channel.owner
    
    # Create credentials from user's refresh token
    if not user or not user.google_refresh_token:
        raise ValueError("User authentication required - no refresh token")
    
    creds = Credentials(
        token=None,
        refresh_token=user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=[
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/youtube.force-ssl",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid"
        ],
    )
    
    # Refresh the token
    creds.refresh(GoogleAuthRequest())
    
    # Initialize YouTube client with credentials
    youtube_client = YouTubeClient(credentials=creds)
```

### Files Changed
- `backend/app/services/ingest_worker.py`

---

## 6. SRT Caption Parsing Error

### Problem
```python
TypeError: a bytes-like object is required, not 'str'
```

YouTube API's `captions().download()` returns bytes, but the parsing function expected a string.

### Root Cause
```python
# captions().download() returns bytes
caption_content = youtube_client.youtube.captions().download(
    id=caption_id,
    tfmt='srt'
).execute()

# But _parse_srt_to_transcript expects str
def _parse_srt_to_transcript(srt_content: str, language: str) -> dict:
    blocks = srt_content.strip().split('\n\n')  # Fails on bytes
```

### Solution
Added decoding step before parsing:
```python
# Download caption content in SRT format
caption_content = youtube_client.youtube.captions().download(
    id=caption_id,
    tfmt='srt'
).execute()

# Decode bytes to string if needed
if isinstance(caption_content, bytes):
    caption_content = caption_content.decode('utf-8')

# Parse SRT to our format
transcript_data = _parse_srt_to_transcript(caption_content, language)
```

### Files Changed
- `backend/app/services/ingest_worker.py`

---

## 7. ChromaDB Version Mismatch

### Problem
```python
KeyError: '_type'
```

When indexing transcripts in ChromaDB vector store, getting key error during collection creation.

### Root Cause
Version incompatibility between ChromaDB client and server:
- Python client: `chromadb==0.6.3` (from requirements.txt)
- Docker image: `chromadb/chroma:latest` (was probably 0.4.x or 0.5.x)
- API response format changed between versions

### Solution
Pinned ChromaDB Docker image to match Python client version:

```yaml
# Before
chromadb:
  image: chromadb/chroma:latest

# After
chromadb:
  image: chromadb/chroma:0.6.3
```

Then rebuilt the container:
```bash
docker-compose stop chromadb
docker-compose up -d chromadb
docker-compose restart worker
```

### Files Changed
- `backend/docker-compose.yml`

### Lessons Learned
- Always pin versions for production dependencies
- Avoid using `:latest` tag for critical services
- Keep client and server versions synchronized

---

## 8. YouTube API Quota

### Problem
```
403 Forbidden - "quotaExceeded"
The request cannot be completed because you have exceeded your quota.
```

### Root Cause
YouTube Data API v3 has daily quota limits:
- **Default quota:** 10,000 units/day
- **Search endpoint:** 100 units per request
- **Captions list:** 50 units per request
- **Video list:** 1 unit per request

Heavy testing exhausted the daily quota.

### Solution
**Short-term:**
- Wait until midnight Pacific Time for quota reset
- Use already processed videos for testing

**Long-term:**
1. Request quota increase in Google Cloud Console:
   - Go to: https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas
   - Production apps can get 1,000,000+ units/day

2. Implement caching:
   - Cache video metadata
   - Avoid redundant API calls
   - Sync only new videos

3. Optimize API usage:
   - Use `videos.list` instead of `search.list` when possible (cheaper)
   - Batch requests where possible
   - Implement exponential backoff for rate limiting

### Not a Bug
This is expected behavior and indicates the system is working correctly!

---

## Environment Variables Summary

### For Docker Worker (`docker-compose.yml`)
```yaml
environment:
  - PYTHONUNBUFFERED=1
  - REDIS_URL=redis://redis:6379/0
  - CHROMA_HOST=${CHROMA_HOST:-chromadb}
  - CHROMA_PORT=${CHROMA_PORT:-8000}
  - DATABASE_URL=postgresql://mayur:jm145200@host.docker.internal:5432/aiyoutuberstudio
  - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
  - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
  - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
  - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
  - AWS_REGION=${AWS_REGION}
  - S3_BUCKET_NAME=${S3_BUCKET_NAME}
  - C_FORCE_ROOT=true
```

### For Local Development (`.env`)
```bash
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://mayur:jm145200@localhost:5432/aiyoutuberstudio
```

---

## Complete Docker Compose Configuration

Final working `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # Celery Worker for Video Processing
  worker:
    build:
      context: .
      dockerfile: Dockerfile
    image: ai-youtuber-backend:latest
    container_name: worker
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - PYTHONUNBUFFERED=1
      - REDIS_URL=redis://redis:6379/0
      - CHROMA_HOST=${CHROMA_HOST:-chromadb}
      - CHROMA_PORT=${CHROMA_PORT:-8000}
      - DATABASE_URL=postgresql://mayur:jm145200@host.docker.internal:5432/aiyoutuberstudio
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_REGION=${AWS_REGION}
      - S3_BUCKET_NAME=${S3_BUCKET_NAME}
      - C_FORCE_ROOT=true
    volumes:
      - ./logs:/app/logs
      - ./app:/app/app
    depends_on:
      - redis
      - chromadb
    networks:
      - app-network
    extra_hosts:
      - "host.docker.internal:host-gateway"
    healthcheck:
      test: ["CMD-SHELL", "celery -A celery_worker inspect ping || exit 1"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 60s
    command: celery -A celery_worker worker --loglevel=info --concurrency=2 --max-tasks-per-child=50 --queues=ingest,transcribe,embedding,generation,insights,celery

  # Redis (Message Broker & Result Backend)
  redis:
    image: redis:7-alpine
    container_name: redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - app-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru

  # ChromaDB Vector Store
  chromadb:
    image: chromadb/chroma:0.6.3
    container_name: chromadb
    restart: unless-stopped
    ports:
      - "8001:8000"
    volumes:
      - chroma-data:/chroma/chroma
    networks:
      - app-network
    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

networks:
  app-network:
    driver: bridge

volumes:
  redis-data:
    driver: local
  chroma-data:
    driver: local
```

---

## Verification & Testing

### Check Docker Services
```bash
cd backend
docker-compose ps
```

Expected output:
```
NAME       SERVICE    STATUS         PORTS
chromadb   chromadb   Up (healthy)   0.0.0.0:8001->8000/tcp
redis      redis      Up (healthy)   0.0.0.0:6379:6379/tcp
worker     worker     Up (healthy)   8000/tcp
```

### Monitor Worker Logs
```bash
docker-compose logs worker --follow
```

### Check Queue Status
```bash
# Check tasks in ingest queue
redis-cli -h localhost -p 6379 LLEN ingest

# Check tasks in celery queue
redis-cli -h localhost -p 6379 LLEN celery

# Monitor all queues
watch -n 1 'redis-cli -h localhost -p 6379 INFO | grep keys'
```

### Test Complete Pipeline
1. Sync videos from frontend
2. Watch worker logs for processing
3. Verify:
   - Captions fetched from YouTube
   - Transcripts uploaded to S3
   - Indexed in ChromaDB
   - Video status = COMPLETE

---

## Success Metrics

After all fixes, the complete video processing pipeline works:

1. ✅ **FastAPI Backend** - Running locally, connected to Redis
2. ✅ **Redis** - Message broker for Celery tasks
3. ✅ **ChromaDB** - Vector store for transcript embeddings
4. ✅ **Celery Worker** - Processing tasks from all queues
5. ✅ **YouTube API** - Fetching videos and captions with proper OAuth
6. ✅ **S3 Storage** - Storing transcripts successfully
7. ✅ **End-to-End** - Videos processed from SYNCED → COMPLETE

---

## Common Commands

### Restart Services
```bash
# Restart worker only
docker-compose restart worker

# Restart all services
docker-compose restart

# Rebuild and restart
docker-compose up -d --build
```

### Clear Queues
```bash
# Clear ingest queue
redis-cli -h localhost -p 6379 DEL ingest

# Clear all celery queues
redis-cli -h localhost -p 6379 FLUSHDB
```

### Check Logs
```bash
# Worker logs
docker-compose logs worker --tail=100

# Redis logs
docker-compose logs redis --tail=50

# ChromaDB logs
docker-compose logs chromadb --tail=50

# Follow all logs
docker-compose logs -f
```

---

## Future Improvements

1. **Add monitoring**
   - Flower for Celery monitoring
   - Prometheus metrics
   - Health check endpoints

2. **Error handling**
   - Retry logic with exponential backoff
   - Dead letter queues
   - Better error notifications

3. **Performance**
   - Increase worker concurrency for production
   - Implement task prioritization
   - Add caching layer

4. **Security**
   - Use Docker secrets for sensitive data
   - Implement rate limiting
   - Add authentication to ChromaDB

---

## Related Documentation

- [Docker Setup Guide](../DOCKER_SETUP.md)
- [Local Setup Instructions](../../LOCAL_SETUP_INSTRUCTIONS.md)
- [Project Architecture](../NEW_ARC.md)

---

**Session Duration:** ~2 hours  
**Issues Resolved:** 8 major issues  
**Files Modified:** 4 files  
**Status:** ✅ Fully Operational

