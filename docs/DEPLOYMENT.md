# AI YouTuber Studio - Deployment Guide

Complete guide to deploy the AI YouTuber Studio backend to EC2 with automatic GitHub Actions deployment.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [EC2 Initial Setup](#ec2-initial-setup)
4. [GitHub Setup](#github-setup)
5. [Deployment Process](#deployment-process)
6. [Vercel Frontend Setup](#vercel-frontend-setup)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────┐
│  Vercel         │
│  (Frontend)     │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────────────────────────┐
│  EC2 Instance                       │
│  ┌──────────────┐                   │
│  │   Nginx      │ (Reverse Proxy)   │
│  │   Port 443   │                   │
│  └──────┬───────┘                   │
│         │                           │
│  ┌──────▼────────────────────────┐  │
│  │   Docker Compose              │  │
│  │                               │  │
│  │  ┌─────────┐   ┌───────────┐ │  │
│  │  │ Backend │   │  Worker   │ │  │
│  │  │ FastAPI │   │  Celery   │ │  │
│  │  └────┬────┘   └─────┬─────┘ │  │
│  │       │              │       │  │
│  │       └──────┬───────┘       │  │
│  │              │               │  │
│  │       ┌──────▼──────┐        │  │
│  │       │   Redis     │        │  │
│  │       └─────────────┘        │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │  ChromaDB    │  │ PostgreSQL  │ │
│  │  (Existing)  │  │ (Existing)  │ │
│  └──────────────┘  └─────────────┘ │
└─────────────────────────────────────┘
```

**Key Points:**
- Frontend on Vercel connects to backend via HTTPS
- Nginx provides SSL termination and reverse proxy
- Backend & Worker run in Docker containers
- Redis runs in container (or use existing on EC2)
- ChromaDB and PostgreSQL are existing services on EC2
- GitHub Actions automates deployment on push to main

---

## Prerequisites

### On Your Local Machine
- Git installed
- GitHub account with repository access
- Access to EC2 instance (SSH key)

### On EC2 Instance
- Ubuntu 20.04/22.04 LTS (recommended)
- Docker & Docker Compose installed
- Nginx installed
- PostgreSQL installed and running
- ChromaDB running on port 8001
- Domain name pointed to EC2 IP (optional but recommended)
- SSL certificate (Let's Encrypt recommended)

---

## EC2 Initial Setup

### 1. Install Required Software

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Install Nginx
sudo apt install nginx -y

# Install Certbot for SSL
sudo apt install certbot python3-certbot-nginx -y
```

### 2. Setup SSL Certificate (if using domain)

```bash
# Replace api.yourdomain.com with your actual domain
sudo certbot --nginx -d api.yourdomain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

### 3. Configure Nginx

```bash
# Copy the nginx config from this repo
sudo cp deployment/nginx-ai-youtuber.conf /etc/nginx/sites-available/ai-youtuber

# Edit the file and replace:
# - api.yourdomain.com with your domain
# - SSL certificate paths if needed
sudo nano /etc/nginx/sites-available/ai-youtuber

# Create symlink
sudo ln -s /etc/nginx/sites-available/ai-youtuber /etc/nginx/sites-enabled/

# Remove default config
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### 4. Setup Deployment Directory

```bash
# Create directory structure
mkdir -p ~/ai-youtuber-studio/backend
cd ~/ai-youtuber-studio/backend

# Create logs directory
mkdir -p logs
```

### 5. Create Environment File

```bash
# Create .env file with your actual values
cat > .env <<'EOF'
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ai_youtuber

# Redis
REDIS_URL=redis://redis:6379/0

# ChromaDB
CHROMA_HOST=host.docker.internal
CHROMA_PORT=8001

# AWS S3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket

# Google OAuth
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=https://your-frontend.vercel.app

# OpenAI
OPENAI_API_KEY=sk-your-key

# Gemini
GEMINI_API_KEY=your-gemini-key

# CORS (your Vercel frontend URL)
BACKEND_CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:3000

# Environment
ENV=production
EOF

# Secure the file
chmod 600 .env
```

### 6. Verify ChromaDB and PostgreSQL

```bash
# Check ChromaDB is running
curl http://localhost:8001/api/v1/heartbeat

# Check PostgreSQL is running
sudo systemctl status postgresql

# Test PostgreSQL connection
psql -U your_user -d ai_youtuber -c "SELECT 1;"
```

---

## GitHub Setup

### 1. Add GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add the following secrets:

```
EC2_HOST=your.ec2.ip.address
EC2_SSH_USER=ubuntu
EC2_SSH_KEY=<paste your private SSH key content>
EC2_SSH_PORT=22

DATABASE_URL=postgresql://user:password@localhost:5432/ai_youtuber
REDIS_URL=redis://redis:6379/0
CHROMA_HOST=host.docker.internal
CHROMA_PORT=8001

AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket

GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=https://your-frontend.vercel.app

OPENAI_API_KEY=sk-your-key
GEMINI_API_KEY=your-gemini-key

BACKEND_CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:3000
```

### 2. Verify GitHub Actions

- Check that `.github/workflows/deploy-backend.yml` exists in your repo
- The workflow will trigger on push to `main` branch
- It will automatically deploy to EC2

---

## Deployment Process

### Automatic Deployment (Recommended)

1. **Make changes to backend code**
2. **Commit and push to main branch:**
   ```bash
   git add .
   git commit -m "Update backend"
   git push origin main
   ```
3. **Watch GitHub Actions:**
   - Go to GitHub → Actions tab
   - Watch the deployment progress
   - Check logs if any issues occur

4. **Verify deployment:**
   ```bash
   # SSH to EC2
   ssh ubuntu@your.ec2.ip

   # Check containers
   cd ~/ai-youtuber-studio/backend
   sudo docker compose -f docker-compose.prod.yml ps

   # Check logs
   sudo docker logs ai-youtuber-backend --tail 100
   sudo docker logs ai-youtuber-worker --tail 100

   # Test API
   curl http://localhost:8000/health
   ```

### Manual Deployment (If needed)

```bash
# SSH to EC2
ssh ubuntu@your.ec2.ip

# Navigate to backend directory
cd ~/ai-youtuber-studio/backend

# Pull latest code (if you manually copied files)
# ... or copy files manually

# Rebuild and restart containers
sudo docker compose -f docker-compose.prod.yml down
sudo docker compose -f docker-compose.prod.yml build --no-cache
sudo docker compose -f docker-compose.prod.yml up -d

# Check status
sudo docker compose -f docker-compose.prod.yml ps

# View logs
sudo docker compose -f docker-compose.prod.yml logs -f
```

---

## Vercel Frontend Setup

### 1. Create Vercel Project

1. Go to [vercel.com](https://vercel.com)
2. Import your GitHub repository (frontend)
3. Configure build settings:
   - Framework: Vite
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Install Command: `npm install`

### 2. Set Environment Variables

In Vercel project settings → Environment Variables:

```
VITE_BACKEND_URL=https://api.yourdomain.com
```

### 3. Deploy

- Vercel will auto-deploy on push to main
- Or click "Deploy" button manually

### 4. Update CORS

After Vercel deployment:
1. Note your Vercel URL (e.g., `https://your-app.vercel.app`)
2. Update `BACKEND_CORS_ORIGINS` in EC2 `.env` file:
   ```bash
   BACKEND_CORS_ORIGINS=https://your-app.vercel.app,https://your-custom-domain.com
   ```
3. Restart backend:
   ```bash
   sudo docker compose -f docker-compose.prod.yml restart backend
   ```

---

## Monitoring & Maintenance

### Check Container Status

```bash
cd ~/ai-youtuber-studio/backend

# View running containers
sudo docker compose -f docker-compose.prod.yml ps

# View logs (follow mode)
sudo docker compose -f docker-compose.prod.yml logs -f

# View specific service logs
sudo docker logs ai-youtuber-backend -f
sudo docker logs ai-youtuber-worker -f
```

### Check Worker Queue Status

```bash
# Enter worker container
sudo docker exec -it ai-youtuber-worker bash

# Check Celery status
celery -A celery_worker inspect active
celery -A celery_worker inspect stats

# Exit container
exit
```

### Monitor Resource Usage

```bash
# Docker stats
sudo docker stats

# System resources
htop
df -h
free -h
```

### Restart Services

```bash
cd ~/ai-youtuber-studio/backend

# Restart all services
sudo docker compose -f docker-compose.prod.yml restart

# Restart specific service
sudo docker compose -f docker-compose.prod.yml restart backend
sudo docker compose -f docker-compose.prod.yml restart worker
```

### Update Environment Variables

```bash
# Edit .env
nano ~/ai-youtuber-studio/backend/.env

# Restart containers to pick up changes
sudo docker compose -f docker-compose.prod.yml restart
```

---

## Troubleshooting

### Backend Not Starting

```bash
# Check logs
sudo docker logs ai-youtuber-backend --tail 200

# Common issues:
# 1. Database connection error - check DATABASE_URL
# 2. Redis connection error - check REDIS_URL
# 3. ChromaDB connection error - check CHROMA_HOST and CHROMA_PORT

# Test database connection
sudo docker exec -it ai-youtuber-backend python3 -c "from app.db.session import engine; print(engine.connect())"
```

### Worker Not Processing Videos

```bash
# Check worker logs
sudo docker logs ai-youtuber-worker --tail 200

# Check if worker can reach Redis
sudo docker exec -it ai-youtuber-worker python3 -c "import redis; r = redis.from_url('redis://redis:6379/0'); print(r.ping())"

# Check Celery status
sudo docker exec -it ai-youtuber-worker celery -A celery_worker inspect active

# Restart worker
sudo docker compose -f docker-compose.prod.yml restart worker
```

### CORS Errors

```bash
# Check CORS configuration in backend
sudo docker exec -it ai-youtuber-backend cat .env | grep CORS

# Update CORS origins
nano ~/ai-youtuber-studio/backend/.env
# Add your frontend URL to BACKEND_CORS_ORIGINS

# Restart backend
sudo docker compose -f docker-compose.prod.yml restart backend
```

### SSL Certificate Issues

```bash
# Check certificate expiry
sudo certbot certificates

# Renew certificate
sudo certbot renew

# Test nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### Deployment Failures

1. **Check GitHub Actions logs** - Go to Actions tab in GitHub
2. **Check SSH connection** - Verify EC2_SSH_KEY is correct
3. **Check disk space on EC2** - `df -h`
4. **Check Docker service** - `sudo systemctl status docker`

### Clean Up Resources

```bash
# Remove stopped containers
sudo docker container prune -f

# Remove unused images
sudo docker image prune -a -f

# Remove unused volumes
sudo docker volume prune -f

# Remove unused networks
sudo docker network prune -f
```

---

## Video Processing Flow

Once deployed, the automatic video processing flow works as follows:

1. **User syncs videos** via frontend:
   - Frontend calls `POST /api/channels/{id}/sync-videos`

2. **Backend fetches videos** from YouTube:
   - Downloads video metadata
   - Saves to database with `processing_status=synced`

3. **Backend automatically queues videos** for processing:
   - Calls `queue_video_processing.delay(video_id, youtube_video_id)`
   - Video enters Celery queue

4. **Worker processes video automatically**:
   - Downloads audio: `status=audio_downloading`
   - Uploads to S3: `status=audio_downloaded`
   - Transcribes audio: `status=transcribing`
   - Saves transcript: `status=transcribed`
   - Indexes in ChromaDB: `status=indexing`
   - Completes: `status=complete`

5. **Frontend polls status** (every 5 seconds):
   - Displays real-time progress
   - Shows errors if any occur
   - Allows retry for failed videos

**No manual steps required - completely automatic!**

---

## Useful Commands Cheatsheet

```bash
# Deployment
git push origin main                              # Trigger auto-deployment

# Container management
sudo docker compose -f docker-compose.prod.yml ps               # Status
sudo docker compose -f docker-compose.prod.yml logs -f          # Logs
sudo docker compose -f docker-compose.prod.yml restart          # Restart all
sudo docker compose -f docker-compose.prod.yml down             # Stop all
sudo docker compose -f docker-compose.prod.yml up -d            # Start all

# Debugging
sudo docker exec -it ai-youtuber-backend bash                   # Enter backend
sudo docker exec -it ai-youtuber-worker bash                    # Enter worker
sudo docker logs ai-youtuber-backend --tail 100 -f              # Backend logs
sudo docker logs ai-youtuber-worker --tail 100 -f               # Worker logs

# Worker status
sudo docker exec -it ai-youtuber-worker celery -A celery_worker inspect active
sudo docker exec -it ai-youtuber-worker celery -A celery_worker inspect stats

# Nginx
sudo nginx -t                                     # Test config
sudo systemctl reload nginx                       # Reload config
sudo systemctl status nginx                       # Check status
sudo tail -f /var/log/nginx/ai-youtuber-error.log # View logs

# SSL
sudo certbot certificates                         # Check certs
sudo certbot renew                                # Renew certs
```

---

## Support

If you encounter issues:
1. Check logs first: `sudo docker compose logs -f`
2. Verify environment variables: `cat .env`
3. Check container status: `sudo docker compose ps`
4. Review troubleshooting section above

For additional help, check application logs in `~/ai-youtuber-studio/backend/logs/`
