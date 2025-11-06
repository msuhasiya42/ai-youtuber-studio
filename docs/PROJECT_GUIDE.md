# AI YouTuber Studio - Complete Project Guide

> Your AI-powered YouTube content creation assistant with RAG-powered script generation, title optimization, and performance insights.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Quick Start (5 Minutes)](#quick-start-5-minutes)
3. [Detailed Setup](#detailed-setup)
4. [Current Infrastructure](#current-infrastructure)
5. [Features & Usage](#features--usage)
6. [Deployment](#deployment)
7. [Troubleshooting](#troubleshooting)
8. [Cost Breakdown](#cost-breakdown)

---

## Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Your Local Machine                  │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │  Frontend  │  │   Backend    │  │   Celery    │ │
│  │  (React)   │  │  (FastAPI)   │  │   Worker    │ │
│  │  :3000     │  │   :8000      │  │             │ │
│  └──────┬─────┘  └──────┬───────┘  └──────┬──────┘ │
│         │               │                  │         │
│         └───────────────┴──────────────────┘         │
│                         │                            │
│              ┌──────────┴──────────────┐             │
│              │   Docker Compose        │             │
│              │   - Redis (queue)       │             │
│              └─────────────────────────┘             │
└─────────────────────────────────────────────────────┘
                          │
                          │ (SSH Tunnels)
                          │
           ┌──────────────┴──────────────┐
           │                             │
    ┌──────▼──────┐              ┌───────▼──────┐
    │   AWS RDS   │              │   EC2 VM     │
    │(PostgreSQL) │              │  (Ubuntu)    │
    │   :5432     │              │              │
    └─────────────┘              │ ┌──────────┐ │
                                 │ │ChromaDB  │ │
    ┌──────────────┐             │ │  :8001   │ │
    │   AWS S3     │             │ └──────────┘ │
    │  (Storage)   │             └──────────────┘
    │              │
    │ - Audio      │
    │ - Transcripts│
    └──────────────┘
```

### Data Flow Pipeline

```mermaid
flowchart TD
    A[YouTube Video ID] --> B[YouTube Data API]
    B --> C[Store Metadata in PostgreSQL]
    B --> D[Download Audio via yt-dlp]
    D --> E[Upload to S3]
    E --> F[Whisper Transcription]
    F --> G[Store Transcript in S3]
    G --> H[Chunk Transcript]
    H --> I[Generate Embeddings]
    I --> J[Store in ChromaDB]
    J --> K[RAG Retrieval]
    K --> L[LLM Script Generation]
    L --> M[Store Generated Content]

    C --> N[Pattern Analyzer]
    N --> O[Title Optimizer]

    M --> P[Dashboard/UI]
    O --> P
```

### Tech Stack

**Backend:**
- FastAPI (Python 3.12+)
- PostgreSQL (AWS RDS) - structured data
- Redis (Docker) - task queue & cache
- ChromaDB (EC2) - vector database for RAG
- Celery - async task processing
- S3 - audio & transcript storage

**Frontend:**
- React 19.2
- TypeScript
- Vite
- React Router DOM

**AI/ML:**
- OpenAI Whisper (transcription)
- Google Gemini or OpenAI GPT (LLM)
- ChromaDB (vector embeddings)

**Infrastructure:**
- Docker Compose (backend orchestration)
- AWS RDS (managed PostgreSQL)
- AWS S3 (object storage)
- EC2 (ChromaDB host)

---

## Quick Start (5 Minutes)

### Prerequisites

- Docker & Docker Compose
- Node.js 18+
- Python 3.12+
- AWS account (RDS, S3, EC2)
- Google OAuth credentials
- OpenAI or Gemini API key

### 1. Clone & Setup Environment

```bash
# Clone repository
git clone https://github.com/your-repo/ai-youtuber-studio.git
cd ai-youtuber-studio

# Backend environment
cd backend
cp .env.example .env
# Edit .env with your credentials (see .env.example for details)

# Frontend environment
cd ../frontend
cp .env.example .env
# Edit .env with backend URL
```

### 2. Start Services

```bash
# Start Docker services (backend, worker, redis)
cd backend
docker-compose up -d

# Run database migrations
docker exec -it ai-youtuber-backend alembic upgrade head

# Start frontend (separate terminal)
cd ../frontend
npm install
npm run dev
```

### 3. Access Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 4. Connect YouTube Channel

1. Navigate to http://localhost:3000
2. Click "Connect YouTube Channel"
3. Authorize with Google OAuth
4. Start syncing videos!

---

## Detailed Setup

### Step 1: AWS Infrastructure Setup

#### 1.1 AWS RDS (PostgreSQL Database)

1. Go to [AWS RDS Console](https://console.aws.amazon.com/rds/)
2. Create database:
   - Engine: PostgreSQL 15+
   - Template: Free tier or Production
   - DB identifier: `ai-youtuber-studio-db`
   - Master username: `postgres`
   - Master password: (save this!)
   - Instance class: `db.t3.micro` (free tier)
   - Storage: 20 GB
   - **Public access: Yes** (for development)
   - Database name: `ai_youtuber_studio`

3. Configure security group:
   - Add inbound rule: PostgreSQL (5432) from your IP

4. Save connection details:
   ```
   Endpoint: your-db.xxxxx.us-east-1.rds.amazonaws.com
   Port: 5432
   Database: ai_youtuber_studio
   ```

#### 1.2 EC2 Instance (ChromaDB)

1. Launch EC2 instance:
   - AMI: Ubuntu Server 22.04 LTS
   - Instance type: `t2.micro` (free tier)
   - Key pair: Create new (save `.pem` file!)
   - Security group: Allow SSH (22), Custom TCP (8001)
   - Storage: 20 GB

2. Connect to EC2 and setup ChromaDB:

```bash
# Make PEM file secure
chmod 400 ~/path/to/your-key.pem

# SSH into EC2
ssh -i ~/path/to/your-key.pem ubuntu@<EC2-PUBLIC-IP>

# Install Docker
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker ubuntu

# Create docker-compose.yml for ChromaDB
cat > docker-compose.yml <<EOF
version: '3.8'
services:
  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma
    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE
    restart: unless-stopped

volumes:
  chroma_data:
EOF

# Start ChromaDB
docker-compose up -d

# Verify it's running
curl http://localhost:8001/api/v1/heartbeat
```

3. Setup SSH tunnel (on your local machine):

```bash
# Create tunnel for ChromaDB access
ssh -i ~/path/to/your-key.pem \
    -N -L 8001:127.0.0.1:8001 \
    ubuntu@<EC2-PUBLIC-IP>

# Keep this terminal open
```

#### 1.3 AWS S3 (Storage)

1. Go to [S3 Console](https://console.aws.amazon.com/s3/)
2. Create bucket:
   - Name: `ai-youtuber-studio-yourname` (globally unique)
   - Region: `us-east-1` (or your preferred region)
   - Block public access: **Keep enabled** (private bucket)

3. Create IAM user:
   - Go to [IAM Console](https://console.aws.amazon.com/iam/)
   - Create user: `ai-youtuber-app`
   - Attach policy: `AmazonS3FullAccess`
   - Create access keys
   - Save: Access Key ID & Secret Access Key

### Step 2: API Keys Setup

#### 2.1 Google OAuth (YouTube Access)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project: "AI YouTuber Studio"
3. Enable APIs:
   - YouTube Data API v3
   - YouTube Analytics API
4. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized redirect URIs: `http://localhost:8000/api/auth/oauth/google/callback`
5. Save: Client ID & Client Secret

#### 2.2 AI Provider (Choose One)

**Option A: Google Gemini (Recommended - Free Tier)**

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Get API key"
3. Create API key in new project
4. Copy key: `AIza...`

**Pricing:**
- Free tier: 15 requests/minute
- Paid: $0.075 per 1M tokens

**Option B: OpenAI**

1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create new secret key
3. Copy key: `sk-proj-...`
4. Add payment method ($5 minimum)

**Pricing:**
- Whisper: $0.006/minute
- GPT-4o-mini: $0.15/$0.60 per 1M tokens

### Step 3: Configure Environment Variables

**Backend (`backend/.env`):**

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your_secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/auth/oauth/google/callback

# Database (AWS RDS)
DATABASE_URL=postgresql://postgres:your_password@your-rds-endpoint.us-east-1.rds.amazonaws.com:5432/ai_youtuber_studio

# Redis (Docker)
REDIS_URL=redis://redis:6379/0

# ChromaDB (via SSH tunnel from EC2)
CHROMA_HOST=host.docker.internal
CHROMA_PORT=8001

# Storage (AWS S3)
STORAGE_TYPE=s3
AWS_S3_BUCKET=ai-youtuber-studio-yourname
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# AI Provider
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIza...
OPENAI_API_KEY=sk-proj-...  # Required for Whisper

# Security
JWT_SECRET=your_very_long_random_secret

# CORS
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Environment
ENV=production
C_FORCE_ROOT=true
```

**Frontend (`frontend/.env`):**

```bash
VITE_BACKEND_URL=http://localhost:8000
VITE_GEMINI_API_KEY=AIza...
```

### Step 4: Initialize Database

```bash
cd backend

# Install dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head
```

### Step 5: Start Application

```bash
# Terminal 1: Start Docker services
cd backend
docker-compose up -d

# Verify services are running
docker-compose ps

# Check logs
docker-compose logs -f

# Terminal 2: Start frontend
cd frontend
npm install
npm run dev
```

### Step 6: Verify Setup

```bash
# Check backend health
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# Check ChromaDB (via tunnel)
curl http://localhost:8001/api/v1/heartbeat

# Check Redis
docker exec -it ai-youtuber-redis redis-cli ping
# Expected: PONG

# Check PostgreSQL
psql "$DATABASE_URL" -c "SELECT 1;"
```

---

## Current Infrastructure

### Docker Compose Services

Your current `backend/docker-compose.yml` includes:

1. **Backend (FastAPI)**
   - Port: 8000
   - Command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
   - Depends on: redis
   - Health check: `curl http://localhost:8000/health`

2. **Worker (Celery)**
   - Command: `celery -A celery_worker worker --loglevel=info --concurrency=2`
   - Depends on: redis, backend
   - Handles: video processing, transcription, embedding

3. **Redis**
   - Port: 6379
   - Purpose: Task queue & cache
   - Memory: 512MB max

### External Services

1. **AWS RDS (PostgreSQL)**
   - Stores: videos, channels, transcripts, insights
   - Connection: Direct via connection string

2. **ChromaDB (EC2)**
   - Stores: vector embeddings for RAG
   - Connection: Via SSH tunnel to `host.docker.internal:8001`

3. **AWS S3**
   - Stores: audio files, transcript JSON
   - Access: boto3 SDK with IAM credentials

### Service Communication

- Frontend → Backend: HTTP REST API
- Backend → PostgreSQL: SQLAlchemy ORM
- Backend → Redis: redis-py
- Backend → ChromaDB: HTTP API (via tunnel)
- Backend → S3: boto3
- Backend → Worker: Celery tasks via Redis

---

## Features & Usage

### 1. YouTube Integration

**Sync Videos:**
```bash
curl -X POST http://localhost:8000/api/channels/1/sync-videos \
  -H "Cookie: user_id=1"
```

**What it does:**
- Fetches last 50 videos from YouTube Data API
- Stores metadata (title, views, likes, duration)
- Returns: new_videos count, updated_videos count

### 2. Video Processing Pipeline

**Process Video:**
```bash
curl -X POST http://localhost:8000/api/content-studio/process-video-pipeline/5 \
  -H "Cookie: user_id=1"
```

**Pipeline steps:**
1. Download audio (yt-dlp) → Upload to S3
2. Transcribe with Whisper → Store transcript in S3
3. Chunk transcript (500 chars, 50 char overlap)
4. Generate embeddings → Store in ChromaDB

**Duration:** 2-5 minutes per video

### 3. AI Content Studio

#### Script Generator

Generate RAG-powered scripts based on your channel's style:

```bash
curl -X POST http://localhost:8000/api/content-studio/generate-script \
  -H "Content-Type: application/json" \
  -H "Cookie: user_id=1" \
  -d '{
    "channel_id": 1,
    "topic": "YouTube growth tips",
    "tone": "conversational",
    "minutes": 8,
    "video_format": "standard"
  }'
```

**Output:**
- Title suggestion
- Hook (first 10 seconds)
- Introduction
- Body sections with timestamps
- Conclusion with CTA
- Visual cues
- Estimated retention points

#### Title Optimizer

Generate and score title variations:

```bash
curl -X POST http://localhost:8000/api/content-studio/generate-titles \
  -H "Content-Type: application/json" \
  -H "Cookie: user_id=1" \
  -d '{
    "channel_id": 1,
    "topic": "viral shorts ideas",
    "count": 5
  }'
```

**Scoring factors:**
- Length (optimal: 50-60 chars)
- Trending keywords from channel
- Pattern matching (how-to, numbers, questions)
- Emotional triggers
- Current year mention

**Output:** 5 titles with scores (0-100), predicted CTR, and grade (A+ to F)

#### Performance Insights

Analyze patterns from top-performing videos:

```bash
curl -X POST http://localhost:8000/api/content-studio/analyze-patterns \
  -H "Content-Type: application/json" \
  -H "Cookie: user_id=1" \
  -d '{"channel_id": 1, "top_n": 10}'
```

**Analysis includes:**
- Common keywords in successful titles
- Average video duration
- Optimal length range
- Engagement rate patterns
- Content themes (AI-extracted)
- Actionable recommendations

---

## Deployment

### Production Deployment Checklist

- [ ] AWS RDS database configured
- [ ] EC2 instance running ChromaDB
- [ ] S3 bucket created with IAM access
- [ ] SSH tunnels configured (or VPC peering)
- [ ] Environment variables set (no .env file in production)
- [ ] Docker images built
- [ ] Frontend built and served via Nginx/CDN
- [ ] SSL certificates configured
- [ ] Monitoring setup (CloudWatch, logs)
- [ ] Backups enabled (RDS snapshots, S3 versioning)

### Docker Deployment

```bash
# Build images
cd backend
docker-compose build

# Start services
docker-compose up -d

# Check health
docker-compose ps
docker-compose logs -f

# Stop services
docker-compose down
```

### Scaling

**Add more Celery workers:**
```bash
# Edit docker-compose.yml to add more worker replicas
docker-compose up -d --scale worker=3
```

**Upgrade database:**
- RDS: Modify instance class in AWS console
- Add read replicas for read-heavy workloads

**Optimize ChromaDB:**
- Use larger EC2 instance
- Or migrate to managed vector DB service

---

## Troubleshooting

### Common Issues

#### 1. SSH Tunnel Connection Refused

**Symptoms:** Can't connect to ChromaDB

**Solutions:**
```bash
# Check tunnel is running
ps aux | grep "ssh.*8001"

# Restart tunnel
ssh -i ~/path/to/key.pem -N -L 8001:127.0.0.1:8001 ubuntu@<EC2-IP>

# Verify ChromaDB on EC2
ssh -i ~/path/to/key.pem ubuntu@<EC2-IP>
docker ps
curl http://localhost:8001/api/v1/heartbeat
```

#### 2. PostgreSQL Connection Failed

**Symptoms:** `psycopg2.OperationalError: could not connect to server`

**Solutions:**
```bash
# Check DATABASE_URL format
echo $DATABASE_URL
# Should be: postgresql://user:pass@host:5432/db

# URL-encode password if it has special characters
python -c "from urllib.parse import quote_plus; print(quote_plus('your_password'))"

# Test connection
psql "$DATABASE_URL" -c "SELECT 1;"

# Check RDS security group allows your IP on port 5432
```

#### 3. Redis Connection Refused

**Symptoms:** Celery tasks not running

**Solutions:**
```bash
# Check Redis container
docker ps | grep redis
docker logs ai-youtuber-redis

# Test Redis
docker exec -it ai-youtuber-redis redis-cli ping

# Restart Redis
docker-compose restart redis
```

#### 4. S3 Access Denied

**Symptoms:** `botocore.exceptions.ClientError: AccessDenied`

**Solutions:**
```bash
# Verify credentials
aws sts get-caller-identity

# Test S3 access
aws s3 ls s3://your-bucket-name/

# Check IAM policy includes S3 permissions
# Ensure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are correct in .env
```

#### 5. Worker Not Processing Tasks

**Symptoms:** Tasks stuck in PENDING state

**Solutions:**
```bash
# Check worker logs
docker logs ai-youtuber-worker

# Restart worker
docker-compose restart worker

# Purge stuck tasks
docker exec -it ai-youtuber-backend celery -A celery_worker purge

# Check Redis connection from worker
docker exec -it ai-youtuber-worker redis-cli -h redis ping
```

#### 6. Frontend Can't Reach Backend

**Symptoms:** `ERR_CONNECTION_REFUSED` in browser

**Solutions:**
```bash
# Check VITE_BACKEND_URL in frontend/.env
cat frontend/.env
# Should be: VITE_BACKEND_URL=http://localhost:8000

# Check backend is running
curl http://localhost:8000/health

# Check CORS settings in backend/.env
# BACKEND_CORS_ORIGINS should include frontend URL
```

### Health Check Commands

```bash
# Full system check
curl http://localhost:8000/health  # Backend
curl http://localhost:8001/api/v1/heartbeat  # ChromaDB
docker exec -it ai-youtuber-redis redis-cli ping  # Redis
psql "$DATABASE_URL" -c "SELECT 1;"  # PostgreSQL

# Check all running containers
docker ps

# View logs
docker-compose logs -f
docker-compose logs backend
docker-compose logs worker
docker-compose logs redis

# Check disk space
df -h

# Check memory
docker stats
```

---

## Cost Breakdown

### Monthly Costs (Estimated)

**Using AWS + Gemini (Recommended):**

| Service | Configuration | Cost |
|---------|--------------|------|
| AWS RDS | db.t3.micro (PostgreSQL) | $15-20 |
| EC2 | t2.micro (ChromaDB) | $0 (free tier 1st year) |
| S3 | 20 GB storage + requests | $1-3 |
| Gemini API | Free tier (15 req/min) | $0-5 |
| **Total** | | **$16-28/month** |

**Using AWS + OpenAI:**

| Service | Configuration | Cost |
|---------|--------------|------|
| AWS RDS | db.t3.micro | $15-20 |
| EC2 | t2.micro | $0 (free tier) |
| S3 | 20 GB | $1-3 |
| OpenAI | Whisper + GPT-4o-mini | $15-25 |
| **Total** | | **$31-48/month** |

### Cost Optimization Tips

1. Use EC2 Reserved Instances (save 40%)
2. Enable S3 Intelligent-Tiering
3. Use Gemini's free tier for development
4. Stop RDS instances during off-hours (dev only)
5. Implement caching to reduce API calls

---

## Architecture Decisions

### Why This Stack?

**Docker Compose:**
- Easy local development
- Consistent environments
- Simple orchestration

**AWS RDS:**
- Managed backups
- Automatic patches
- High availability options

**ChromaDB:**
- Simple HTTP API
- Fast semantic search
- Easy to self-host

**Celery:**
- Reliable task processing
- Scalable workers
- Built-in retry logic

**S3:**
- Cost-effective storage
- Durable (99.999999999%)
- Easy to use

### RAG vs Fine-tuning

We chose RAG because:
- Faster iteration (no training)
- Uses latest videos immediately
- Preserves creator's style
- More cost-effective

---

## Support & Contributing

**Issues:** [GitHub Issues](https://github.com/your-repo/ai-youtuber-studio/issues)

**API Documentation:** http://localhost:8000/docs

**Contact:** your-email@example.com

---

**Last Updated:** 2025-11-06

**Version:** 2.0

**Status:** Production Ready
