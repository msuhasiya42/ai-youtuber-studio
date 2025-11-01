# Complete Setup Guide - AI YouTuber Studio

## 🚀 Step-by-Step Setup

This guide will help you set up all required services from scratch.

**Choose your setup path:**
- **Production/Cloud:** Follow section 0️⃣ (AWS Production Setup) - Recommended
- **Local Development:** Follow sections 1️⃣-6️⃣ (Docker/Local setup)

---

## 0️⃣ AWS Production Setup (Recommended)

This section covers setting up the production-ready AWS infrastructure with RDS, EC2, and S3.

### Prerequisites
- AWS Account with billing enabled
- SSH client installed
- Basic understanding of AWS services

### Architecture Overview
```
┌─────────────────────────────────────────────────────┐
│                  Your Local Machine                  │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │  Backend   │  │ Celery Worker│  │  Frontend   │ │
│  │  (FastAPI) │  │              │  │   (React)   │ │
│  └─────┬──────┘  └──────┬───────┘  └──────┬──────┘ │
│        │                │                  │         │
│        └────────────────┴──────────────────┘         │
│                         │                            │
│              ┌──────────┴──────────────┐             │
│              │   SSH Tunnels (via PEM) │             │
│              └──────────┬──────────────┘             │
└─────────────────────────┼────────────────────────────┘
                          │
           ┌──────────────┴──────────────┐
           │                             │
    ┌──────▼──────┐              ┌───────▼──────┐
    │   EC2 VM    │              │   AWS RDS    │
    │  (Ubuntu)   │              │ (PostgreSQL) │
    │             │              └──────────────┘
    │ ┌─────────┐ │
    │ │  Redis  │ │              ┌──────────────┐
    │ └─────────┘ │              │   AWS S3     │
    │ ┌─────────┐ │              │ (Storage)    │
    │ │ChromaDB │ │              └──────────────┘
    │ └─────────┘ │
    └─────────────┘
```

### Step 1: Setup AWS RDS (PostgreSQL Database)

1. **Go to RDS**: https://console.aws.amazon.com/rds/
2. **Create Database**:
   - Click "Create database"
   - Engine: PostgreSQL (version 15 or later)
   - Template: Free tier (or Production based on needs)
   - DB instance identifier: `ai-youtuber-studio-db`
   - Master username: `postgres`
   - Master password: Create strong password (save it!)
   - DB instance class: db.t3.micro (free tier) or larger
   - Storage: 20 GB (auto-scaling enabled)
   - VPC: Default VPC
   - Public access: **Yes** (for development)
   - VPC security group: Create new
   - Database name: `ai_youtuber_studio`
   - Click "Create database"

3. **Configure Security Group**:
   - Once database is created, go to its security group
   - Add inbound rule:
     - Type: PostgreSQL
     - Port: 5432
     - Source: My IP (or 0.0.0.0/0 for development)

4. **Get Connection String**:
   ```
   Endpoint: ai-youtuber-studio-db.xxxxx.us-east-1.rds.amazonaws.com
   Port: 5432
   Database: ai_youtuber_studio
   ```

### Step 2: Setup EC2 for Redis & ChromaDB

1. **Launch EC2 Instance**:
   - Go to: https://console.aws.amazon.com/ec2/
   - Click "Launch instances"
   - Name: `ai-youtuber-studio-services`
   - AMI: Ubuntu Server 22.04 LTS
   - Instance type: t2.micro (free tier) or t2.small
   - Key pair: Create new key pair
     - Name: `ai-youtuber-studio-key`
     - Type: RSA
     - Format: .pem
     - **Download and save the .pem file!**
   - Network settings:
     - Allow SSH (port 22) from My IP
   - Storage: 20 GB
   - Click "Launch instance"

2. **Configure Security Group** (after instance is running):
   - Select your instance
   - Go to Security tab → Security groups
   - Add inbound rules:
     - SSH (port 22) from My IP
     - Custom TCP (port 6379) from My IP (Redis)
     - Custom TCP (port 8001) from My IP (ChromaDB)

3. **Connect to EC2 and Install Docker**:
   ```bash
   # Make PEM file secure
   chmod 400 ~/Downloads/ai-youtuber-studio-key.pem

   # SSH into EC2
   ssh -i ~/Downloads/ai-youtuber-studio-key.pem ubuntu@<EC2-PUBLIC-IP>

   # Install Docker
   sudo apt update
   sudo apt install -y docker.io docker-compose
   sudo usermod -aG docker ubuntu

   # Log out and log back in for group changes
   exit
   ssh -i ~/Downloads/ai-youtuber-studio-key.pem ubuntu@<EC2-PUBLIC-IP>
   ```

4. **Setup Redis & ChromaDB on EC2**:
   ```bash
   # Create docker-compose.yml
   cat > docker-compose.yml <<EOF
   version: '3.8'

   services:
     redis:
       image: redis:7-alpine
       ports:
         - "6379:6379"
       volumes:
         - redis_data:/data
       command: redis-server --appendonly yes
       restart: unless-stopped

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
     redis_data:
     chroma_data:
   EOF

   # Start services
   docker-compose up -d

   # Verify services are running
   docker-compose ps
   curl http://localhost:8001/api/v1/heartbeat  # Should return heartbeat
   ```

### Step 3: Setup SSH Tunnels (Local Machine)

Since Redis and ChromaDB are running on EC2, you need SSH tunnels to access them securely from your local machine.

1. **Move PEM key to secure location**:
   ```bash
   mkdir -p ~/Desktop/AWS
   mv ~/Downloads/ai-youtuber-studio-key.pem ~/Desktop/AWS/
   chmod 400 ~/Desktop/AWS/ai-youtuber-studio-key.pem
   ```

2. **Use the provided startup script**:
   ```bash
   cd /path/to/ai-youtuber-studio
   ./scripts/start_tunnels.sh
   ```

   Or manually create tunnels:
   ```bash
   ssh -i ~/Desktop/AWS/ai-youtuber-studio-key.pem \
       -N -L 6379:127.0.0.1:6379 \
       -L 8001:127.0.0.1:8001 \
       ubuntu@<EC2-PUBLIC-IP>
   ```

3. **Verify tunnels**:
   ```bash
   # Test Redis
   redis-cli -h 127.0.0.1 -p 6379 ping  # Should return PONG

   # Test ChromaDB
   curl http://127.0.0.1:8001/api/v1/heartbeat  # Should return heartbeat
   ```

### Step 4: Configure Environment Variables

Create `backend/.env` using the template:

```bash
cd backend
cp .env.example .env
```

Update with your AWS values:

```bash
# PostgreSQL (RDS)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@your-rds-endpoint.us-east-1.rds.amazonaws.com:5432/ai_youtuber_studio

# Redis (via SSH tunnel to EC2)
REDIS_URL=redis://127.0.0.1:6379/0

# ChromaDB (via SSH tunnel to EC2)
CHROMA_HOST=127.0.0.1
CHROMA_PORT=8001

# AWS S3 (follow section 1️⃣ below)
STORAGE_TYPE=s3
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Google OAuth (follow section 7️⃣ below)
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

# LLM (Gemini or OpenAI - follow sections 3️⃣ or 4️⃣)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key  # Required for Whisper transcription

JWT_SECRET=generate_a_random_string_here
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Step 5: Initialize Database

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head
```

### Step 6: Test All Connections

Use the provided test script:

```bash
./scripts/test_connections.py
```

All services should show ✓ PASS.

### Step 7: Start the Application

```bash
# Start all services (opens new terminals)
./scripts/start_all.sh

# Or manually in separate terminals:
# Terminal 1: Backend
./scripts/start_backend.sh

# Terminal 2: Worker
./scripts/start_worker.sh

# Terminal 3: Frontend
cd frontend
npm install
npm run dev
```

### Cost Estimate (AWS)

- **RDS db.t3.micro**: ~$15-20/month
- **EC2 t2.micro (free tier)**: $0 first year, then ~$8-10/month
- **S3 Storage**: ~$1-3/month (for 10-20 GB)
- **Data Transfer**: ~$1-2/month

**Total: ~$0-5/month (first year with free tier), then ~$25-35/month**

---

## 1️⃣ AWS S3 Setup (Storage for Audio & Transcripts)

### Step 1: Create S3 Bucket

1. **Login to AWS Console**: https://console.aws.amazon.com/s3/
2. **Create Bucket**:
   - Click "Create bucket"
   - Bucket name: `ai-youtuber-studio-{your-username}` (must be globally unique)
   - Region: Choose closest to you (e.g., `us-east-1`)
   - **Block Public Access**: Keep all checkboxes checked (private bucket)
   - Click "Create bucket"

### Step 2: Create IAM User for Programmatic Access

1. **Go to IAM**: https://console.aws.amazon.com/iam/
2. **Create User**:
   - Click "Users" → "Create user"
   - Username: `ai-youtuber-studio-app`
   - Click "Next"
3. **Set Permissions**:
   - Select "Attach policies directly"
   - Search and select: **AmazonS3FullAccess** (or create custom policy below)
   - Click "Next" → "Create user"

### Step 3: Create Access Keys

1. **Select the user** you just created
2. **Security credentials** tab
3. **Create access key**:
   - Use case: "Application running on AWS compute service"
   - Click "Next"
   - Description: "AI YouTuber Studio Backend"
   - Click "Create access key"
4. **IMPORTANT**: Copy and save:
   - Access key ID: `AKIA...`
   - Secret access key: `wJalr...` (only shown once!)

### Step 4: (Optional) Create Custom IAM Policy

For better security, create a policy that only allows access to your bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::ai-youtuber-studio-{your-username}",
        "arn:aws:s3:::ai-youtuber-studio-{your-username}/*"
      ]
    }
  ]
}
```

### Step 5: Update Environment Variables

```bash
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=AKIA...your_access_key
AWS_SECRET_ACCESS_KEY=wJalr...your_secret_key
AWS_S3_BUCKET=ai-youtuber-studio-{your-username}
AWS_REGION=us-east-1

# Set storage type
STORAGE_TYPE=s3  # Use 's3' for AWS, 'minio' for local MinIO
```

---

## 2️⃣ ChromaDB Setup (Vector Database)

### Option A: Docker (Recommended)

Add to your `docker-compose.yml`:

```yaml
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

volumes:
  chroma_data:
```

Then start:
```bash
docker-compose up -d chroma
```

### Option B: Standalone Installation

```bash
# Install ChromaDB
pip install chromadb

# Run ChromaDB server
chroma run --host 0.0.0.0 --port 8001
```

### Verify ChromaDB is Running

```bash
# Test heartbeat
curl http://localhost:8001/api/v1/heartbeat

# Expected response: {"nanosecond heartbeat": 1234567890}
```

### Environment Variables

```bash
CHROMA_HOST=localhost
CHROMA_PORT=8001
```

---

## 3️⃣ OpenAI API Key

### Step 1: Get API Key

1. **Go to**: https://platform.openai.com/api-keys
2. **Sign up** or **Login**
3. **Create new secret key**:
   - Name: "AI YouTuber Studio"
   - Click "Create secret key"
4. **Copy the key**: `sk-proj-...` (only shown once!)

### Step 2: Add Credits (if needed)

- Go to https://platform.openai.com/account/billing
- Add payment method
- Minimum: $5 credit recommended

### Pricing (as of 2025)

- **Whisper API**: $0.006 per minute of audio
- **GPT-4o-mini**: $0.15 per 1M input tokens, $0.60 per 1M output tokens
- **Embeddings**: $0.02 per 1M tokens

**Example costs:**
- Transcribe 10 videos (10 min each): ~$0.60
- Generate 50 scripts: ~$2-5
- Total monthly (moderate use): **$10-20**

### Environment Variables

```bash
OPENAI_API_KEY=sk-proj-your_openai_key_here
LLM_PROVIDER=openai
```

---

## 4️⃣ Google Gemini API (Alternative to OpenAI)

### Step 1: Get API Key

1. **Go to**: https://makersuite.google.com/app/apikey
2. **Sign in** with Google account
3. **Create API key**:
   - Click "Get API key"
   - Select "Create API key in new project" or use existing
4. **Copy the key**: `AIza...`

### Pricing (FREE tier available!)

- **Gemini 1.5 Flash**:
  - **FREE tier**: 15 requests per minute
  - **Paid**: $0.075 per 1M input tokens, $0.30 per 1M output tokens
- **Gemini 1.5 Pro**: Higher cost but better quality

**Recommendation**: Start with Gemini Flash (cheaper + free tier)

### Environment Variables

```bash
GEMINI_API_KEY=AIza...your_gemini_key_here
LLM_PROVIDER=gemini
```

---

## 5️⃣ Redis Setup (Cache & Task Queue)

### Option A: Docker (Recommended)

Already in `docker-compose.yml`:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
```

Start:
```bash
docker-compose up -d redis
```

### Option B: Local Installation

**Mac:**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
```

**Windows:**
Download from: https://github.com/microsoftarchive/redis/releases

### Verify Redis

```bash
# Test connection
redis-cli ping
# Expected: PONG

# Or via Docker
docker exec -it ai-youtuber-studio-redis-1 redis-cli ping
```

### Environment Variables

```bash
REDIS_URL=redis://localhost:6379/0

# Or if using Docker:
REDIS_URL=redis://redis:6379/0
```

---

## 6️⃣ PostgreSQL Setup (Database)

### Option A: Docker (Recommended)

Already in `docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: ai_youtube_studio
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

Start:
```bash
docker-compose up -d postgres
```

### Option B: Local Installation

**Mac:**
```bash
brew install postgresql@15
brew services start postgresql@15
createdb ai_youtube_studio
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo -u postgres createdb ai_youtube_studio
```

### Run Migrations

```bash
cd backend
alembic upgrade head
```

### Environment Variables

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_youtube_studio

# Or if using Docker:
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/ai_youtube_studio
```

---

## 7️⃣ Google OAuth Setup (YouTube Access)

### Step 1: Create Google Cloud Project

1. **Go to**: https://console.cloud.google.com/
2. **Create new project**: "AI YouTuber Studio"
3. **Enable APIs**:
   - YouTube Data API v3
   - YouTube Analytics API
   - Google+ API (for user info)

### Step 2: Create OAuth 2.0 Credentials

1. **Go to**: https://console.cloud.google.com/apis/credentials
2. **Configure OAuth consent screen**:
   - User Type: External
   - App name: "AI YouTuber Studio"
   - User support email: your email
   - Scopes: Add YouTube scopes
   - Test users: Add your email
3. **Create OAuth client ID**:
   - Application type: Web application
   - Name: "AI YouTuber Studio Backend"
   - Authorized redirect URIs:
     - `http://localhost:3000` (for local dev)
     - `https://yourdomain.com` (for production)
4. **Download credentials** or copy:
   - Client ID: `123456789.apps.googleusercontent.com`
   - Client Secret: `GOCSPX-...`

### Environment Variables

```bash
GOOGLE_CLIENT_ID=123456789.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:3000
```

---

## 8️⃣ Complete .env File

Create `backend/.env`:

```bash
# ===== GOOGLE OAUTH =====
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your_secret
GOOGLE_REDIRECT_URI=http://localhost:3000

# ===== AI PROVIDER (Choose ONE) =====
LLM_PROVIDER=gemini

# Option 1: Gemini (Recommended - has free tier)
GEMINI_API_KEY=AIza...your_gemini_key

# Option 2: OpenAI (Better quality, costs money)
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-proj-...your_openai_key

# ===== STORAGE (AWS S3) =====
STORAGE_TYPE=s3
AWS_ACCESS_KEY_ID=AKIA...your_access_key
AWS_SECRET_ACCESS_KEY=wJalr...your_secret_key
AWS_S3_BUCKET=ai-youtuber-studio-yourname
AWS_REGION=us-east-1

# OR use MinIO for local development
# STORAGE_TYPE=minio
# MINIO_ENDPOINT=localhost:9000
# MINIO_ACCESS_KEY=minioadmin
# MINIO_SECRET_KEY=minioadmin
# MINIO_BUCKET=youtube-data

# ===== VECTOR DATABASE =====
CHROMA_HOST=localhost
CHROMA_PORT=8001

# ===== CACHE & QUEUE =====
REDIS_URL=redis://localhost:6379/0

# ===== DATABASE =====
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_youtube_studio

# ===== BACKEND CONFIG =====
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# ===== OPTIONAL: MinIO Console (if using MinIO) =====
# MINIO_CONSOLE_PORT=9001
```

Create `frontend/.env`:

```bash
VITE_BACKEND_URL=http://localhost:8000
VITE_GEMINI_API_KEY=AIza...your_gemini_key
```

---

## 9️⃣ Installation Steps

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Mac/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start backend server
uvicorn app.main:app --reload --port 8000
```

### Start Celery Worker (Separate Terminal)

```bash
cd backend
source venv/bin/activate

celery -A celery_worker worker --loglevel=info
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

---

## 🔟 Verify Everything Works

### 1. Check Services

```bash
# Backend health
curl http://localhost:8000/health

# ChromaDB
curl http://localhost:8001/api/v1/heartbeat

# Redis
redis-cli ping

# PostgreSQL
psql -U postgres -d ai_youtube_studio -c "SELECT 1;"
```

### 2. Check AWS S3

```bash
# Install AWS CLI
pip install awscli

# Configure
aws configure
# Enter: Access Key ID, Secret Key, Region, output format (json)

# Test bucket access
aws s3 ls s3://ai-youtuber-studio-yourname/
```

### 3. Open Frontend

```bash
open http://localhost:3000
```

### 4. Test OAuth Flow

1. Click "Connect YouTube Channel"
2. Authorize with Google
3. Should redirect to Dashboard

---

## 🐳 Docker Compose (All-in-One)

Update your `backend/docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: ai_youtube_studio
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma
    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE

  # Optional: MinIO (if not using AWS S3)
  # minio:
  #   image: minio/minio:latest
  #   command: server /data --console-address ":9001"
  #   ports:
  #     - "9000:9000"
  #     - "9001:9001"
  #   environment:
  #     MINIO_ROOT_USER: minioadmin
  #     MINIO_ROOT_PASSWORD: minioadmin
  #   volumes:
  #     - minio_data:/data

volumes:
  postgres_data:
  redis_data:
  chroma_data:
  # minio_data:
```

Start all services:

```bash
cd backend
docker-compose up -d
```

---

## 💰 Cost Breakdown

### Using AWS + Gemini (Recommended)

**AWS S3:**
- Storage: $0.023 per GB/month
- Requests: $0.005 per 1,000 PUT, $0.0004 per 1,000 GET
- Expected: **$1-3/month** for 10-20 GB

**Gemini API (FREE tier):**
- 15 requests/minute for free
- After free tier: **$5-10/month** for moderate use

**Total: ~$5-15/month**

### Using AWS + OpenAI (Better quality)

**AWS S3:** $1-3/month
**OpenAI:**
- Whisper: $0.006/min
- GPT-4o-mini: ~$10-20/month for moderate use

**Total: ~$15-30/month**

---

## 🔧 Troubleshooting

### Issue: AWS S3 Access Denied

```bash
# Check credentials
aws sts get-caller-identity

# Verify bucket exists
aws s3 ls

# Test upload
echo "test" > test.txt
aws s3 cp test.txt s3://your-bucket/test.txt
```

### Issue: ChromaDB Connection Failed

```bash
# Check if running
curl http://localhost:8001/api/v1/heartbeat

# Check Docker logs
docker-compose logs chroma

# Restart
docker-compose restart chroma
```

### Issue: Redis Connection Refused

```bash
# Check if running
redis-cli ping

# Check Docker
docker-compose logs redis

# Restart
docker-compose restart redis
```

### Issue: Database Migration Failed

```bash
# Reset migrations
alembic downgrade base
alembic upgrade head

# Or recreate database
dropdb ai_youtube_studio
createdb ai_youtube_studio
alembic upgrade head
```

---

## 🚀 Quick Start Commands

```bash
# Start all infrastructure
cd backend
docker-compose up -d

# Start backend
uvicorn app.main:app --reload

# Start Celery worker (new terminal)
celery -A celery_worker worker --loglevel=info

# Start frontend (new terminal)
cd frontend
npm run dev

# Open browser
open http://localhost:3000
```

---

## ✅ Setup Checklist

- [ ] AWS S3 bucket created
- [ ] AWS IAM user with access keys
- [ ] ChromaDB running (Docker or standalone)
- [ ] Redis running
- [ ] PostgreSQL running
- [ ] OpenAI or Gemini API key obtained
- [ ] Google OAuth credentials created
- [ ] `.env` files created (backend + frontend)
- [ ] Dependencies installed (`pip install`, `npm install`)
- [ ] Database migrations run (`alembic upgrade head`)
- [ ] All services verified with health checks
- [ ] Frontend accessible at `localhost:3000`
- [ ] OAuth flow working

---

**🎉 You're ready to build AI-powered YouTube content!**

Need help with any step? Check the error messages and consult the Troubleshooting section above.
