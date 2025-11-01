# Quick Start Guide - AI Content Studio

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Docker & Docker Compose
- Node.js 18+
- Python 3.12+
- Google OAuth credentials
- OpenAI or Gemini API key

---

## Step 1: Environment Setup

### Backend Configuration

Create `backend/.env`:
```bash
# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:3000

# AI Provider (choose one)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
# OR
# LLM_PROVIDER=openai
# OPENAI_API_KEY=your_openai_key

# Services (default values for Docker)
CHROMA_HOST=chroma
CHROMA_PORT=8000
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=youtube-data
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/ai_youtube_studio

# CORS
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Frontend Configuration

Create `frontend/.env`:
```bash
VITE_BACKEND_URL=http://localhost:8000
VITE_GEMINI_API_KEY=your_gemini_api_key
```

---

## Step 2: Start Services

### Option A: Full Docker Stack (Recommended)

```bash
cd backend
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- MinIO (port 9000, 9001)
- ChromaDB (port 8001)
- FastAPI backend (port 8000)
- Celery workers

### Option B: Local Development

```bash
# Start infrastructure only
cd backend
docker-compose up -d postgres redis minio chroma

# Start backend locally
python -m uvicorn app.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A celery_worker worker --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on: http://localhost:5173 or http://localhost:3000

---

## Step 3: First-Time Setup

### 1. Connect YouTube Channel

1. Open http://localhost:3000
2. Click "Connect YouTube Channel"
3. Authorize with Google OAuth
4. You'll be redirected to Dashboard

### 2. Sync Your Videos

```bash
# Option 1: Via API
curl -X POST http://localhost:8000/api/channels/1/sync-videos \
  -H "Cookie: user_id=1" \
  -b cookies.txt

# Option 2: Via UI (Coming Soon)
# Dashboard → Sync Videos button
```

### 3. Process Videos for AI

Pick 5-10 of your top-performing videos and process them:

```bash
# Process video ID 5 (download audio, transcribe, index)
curl -X POST http://localhost:8000/api/content-studio/process-video-pipeline/5 \
  -H "Cookie: user_id=1" \
  -b cookies.txt
```

**This takes 2-5 minutes per video:**
- Audio download: ~30 seconds
- Whisper transcription: 1-3 minutes
- Vector indexing: ~10 seconds

---

## Step 4: Use AI Content Studio

### Via UI (Easiest)

1. Dashboard → Click "🎬 AI Content Studio"
2. You'll see 3 tabs:

#### **Tab 1: Script Generator**
- Enter topic: "How to increase YouTube watch time"
- Select tone: Conversational
- Duration: 8 minutes
- Format: Standard
- Click "Generate Script"
- Wait 10-30 seconds
- Get full script with hook, body, conclusion, visual cues

#### **Tab 2: Title Optimizer**
- Enter topic: "YouTube growth tips"
- Click "Generate Title Variations"
- Get 5 titles ranked by score
- Copy best title (A+ grade)

#### **Tab 3: Performance Insights**
- Automatically loads when you open tab
- See: Top keywords, optimal duration, engagement patterns
- Get personalized recommendations

### Via API

```bash
# 1. Analyze Patterns
curl -X POST http://localhost:8000/api/content-studio/analyze-patterns \
  -H "Content-Type: application/json" \
  -H "Cookie: user_id=1" \
  -d '{"channel_id": 1, "top_n": 10}'

# 2. Generate Script
curl -X POST http://localhost:8000/api/content-studio/generate-script \
  -H "Content-Type: application/json" \
  -H "Cookie: user_id=1" \
  -d '{
    "channel_id": 1,
    "topic": "YouTube SEO tips",
    "tone": "professional",
    "minutes": 10,
    "video_format": "tutorial"
  }'

# 3. Generate Titles
curl -X POST http://localhost:8000/api/content-studio/generate-titles \
  -H "Content-Type: application/json" \
  -H "Cookie: user_id=1" \
  -d '{"channel_id": 1, "topic": "viral content ideas", "count": 5}'
```

---

## Step 5: Verify Everything Works

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health
# Response: {"status":"ok"}

# API docs
open http://localhost:8000/docs

# MinIO console
open http://localhost:9001
# Login: minioadmin / minioadmin

# Check ChromaDB
curl http://localhost:8001/api/v1/heartbeat
```

### Database Check

```bash
# Connect to PostgreSQL
docker exec -it ai-youtuber-studio-postgres-1 psql -U postgres -d ai_youtube_studio

# Check tables
\dt

# Check videos
SELECT id, title, youtube_video_id, views FROM videos LIMIT 5;

# Check if transcripts exist
SELECT id, title, transcript_s3_key FROM videos WHERE transcript_s3_key IS NOT NULL;
```

### Check Vector Store

```bash
# Get collection stats
curl -X POST http://localhost:8000/api/content-studio/insights/1 \
  -H "Cookie: user_id=1"

# Should show: indexed_chunks > 0 if videos are processed
```

---

## Troubleshooting

### Issue: "No videos found for analysis"

**Solution:** Sync videos first
```bash
curl -X POST http://localhost:8000/api/channels/1/sync-videos
```

### Issue: "Transcript not found"

**Solution:** Process video pipeline
```bash
curl -X POST http://localhost:8000/api/content-studio/process-video-pipeline/VIDEO_ID
```

### Issue: "Failed to generate script - no context"

**Solution:** Index at least 3-5 videos first
```bash
# Process multiple videos
for id in 1 2 3 4 5; do
  curl -X POST http://localhost:8000/api/content-studio/process-video-pipeline/$id \
    -H "Cookie: user_id=1"
  sleep 60  # Wait 1 minute between videos
done
```

### Issue: Celery tasks not running

**Check Celery worker:**
```bash
docker-compose logs celery-worker

# Restart if needed
docker-compose restart celery-worker
```

### Issue: ChromaDB connection error

**Check ChromaDB:**
```bash
docker-compose ps chroma
curl http://localhost:8001/api/v1/heartbeat

# Restart if needed
docker-compose restart chroma
```

### Issue: MinIO upload failed

**Check MinIO:**
```bash
docker-compose logs minio
open http://localhost:9001

# Check bucket exists
# Login → Buckets → should see "youtube-data"
```

---

## Development Tips

### Hot Reload

**Backend:**
```bash
# Auto-reloads on file changes
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
# Auto-reloads on file changes
npm run dev
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery-worker
docker-compose logs -f chroma
```

### Reset Everything

```bash
# Stop all services
docker-compose down -v

# Remove all data (WARNING: deletes everything)
docker volume prune

# Start fresh
docker-compose up -d
```

### Database Migrations

```bash
# Create migration
cd backend
alembic revision --autogenerate -m "description"

# Run migrations
alembic upgrade head
```

---

## Performance Optimization

### Parallel Video Processing

Process multiple videos at once:

```python
# backend/scripts/process_batch.py
import asyncio
from app.services.ingest_worker import download_audio
from app.services.transcribe_worker import transcribe_audio

async def process_videos(video_ids):
    tasks = []
    for vid in video_ids:
        task = download_audio.delay(vid)
        tasks.append(task)

    # Wait for all to complete
    results = await asyncio.gather(*tasks)
    return results

# Run: python -m scripts.process_batch
```

### Optimize Embeddings

Use smaller model for faster processing:

```python
# In vector_store.py
# Switch to faster embedding model
self.llm_provider = get_llm_provider()  # Uses gemini-1.5-flash (fast)
```

---

## Production Deployment

### Environment Variables (Production)

```bash
# Use production URLs
BACKEND_CORS_ORIGINS=https://yourdomain.com
DATABASE_URL=postgresql://user:pass@prod-db:5432/ai_youtube_studio
REDIS_URL=redis://prod-redis:6379/0
MINIO_ENDPOINT=prod-minio:9000
MINIO_SECURE=true

# Use SSL
MINIO_SECURE=true

# Scale Celery workers
CELERY_CONCURRENCY=4
```

### Docker Compose Production

```yaml
services:
  celery-worker:
    deploy:
      replicas: 3  # 3 workers for parallel processing
    environment:
      CELERY_CONCURRENCY: 4
```

### Monitoring

Add health check endpoints:

```bash
# Check system status
curl http://localhost:8000/api/health

# Expected response:
{
  "status": "healthy",
  "services": {
    "database": "ok",
    "redis": "ok",
    "chroma": "ok",
    "minio": "ok"
  }
}
```

---

## API Examples

### Complete Workflow Example

```bash
#!/bin/bash
# complete_workflow.sh

CHANNEL_ID=1
USER_COOKIE="user_id=1"
API_URL="http://localhost:8000"

echo "Step 1: Sync videos from YouTube..."
curl -X POST "$API_URL/api/channels/$CHANNEL_ID/sync-videos" \
  -H "Cookie: $USER_COOKIE"

echo "\nStep 2: Get video list..."
VIDEOS=$(curl -s "$API_URL/api/videos?page=1&page_size=5" \
  -H "Cookie: $USER_COOKIE")

echo "\nStep 3: Process top 3 videos..."
for video_id in 1 2 3; do
  echo "Processing video $video_id..."
  curl -X POST "$API_URL/api/content-studio/process-video-pipeline/$video_id" \
    -H "Cookie: $USER_COOKIE"
  sleep 180  # Wait 3 minutes per video
done

echo "\nStep 4: Analyze patterns..."
curl -X POST "$API_URL/api/content-studio/analyze-patterns" \
  -H "Content-Type: application/json" \
  -H "Cookie: $USER_COOKIE" \
  -d '{"channel_id": '$CHANNEL_ID', "top_n": 10}'

echo "\nStep 5: Generate script..."
curl -X POST "$API_URL/api/content-studio/generate-script" \
  -H "Content-Type: application/json" \
  -H "Cookie: $USER_COOKIE" \
  -d '{
    "channel_id": '$CHANNEL_ID',
    "topic": "YouTube growth strategies",
    "tone": "conversational",
    "minutes": 8,
    "video_format": "standard"
  }'

echo "\nStep 6: Generate titles..."
curl -X POST "$API_URL/api/content-studio/generate-titles" \
  -H "Content-Type: application/json" \
  -H "Cookie: $USER_COOKIE" \
  -d '{"channel_id": '$CHANNEL_ID', "topic": "viral video ideas", "count": 5}'

echo "\n✅ Complete workflow finished!"
```

Run:
```bash
chmod +x complete_workflow.sh
./complete_workflow.sh
```

---

## Next Steps

1. **Process your top 10 videos** to train the AI on your style
2. **Generate your first script** using the Content Studio
3. **Optimize a title** before publishing your next video
4. **Review insights** weekly to track patterns
5. **Share feedback** - what features would help you most?

---

## Support

- **Documentation**: See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **API Docs**: http://localhost:8000/docs
- **Issues**: Create an issue in the repo

---

**🎉 You're ready to use AI Content Studio!**

Start by syncing your videos and processing your top performers. The AI will learn from your successful content and help you create even better videos.
