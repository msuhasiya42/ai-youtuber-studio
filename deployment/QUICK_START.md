# Quick Start Guide - EC2 Deployment

## Overview

This guide will help you deploy the AI YouTuber Studio backend to EC2 with **automatic GitHub Actions deployment** and **automatic video processing**.

## What You Get

✅ **Zero Manual Steps** - Push to GitHub, automatic deployment
✅ **Automatic Video Processing** - Sync videos → Worker processes automatically
✅ **Docker Everything** - Backend & Worker in containers
✅ **Production Ready** - Nginx reverse proxy with SSL
✅ **Monitoring** - Health checks and logging built-in

---

## Architecture

```
Frontend (Vercel) → Nginx (EC2) → Backend (Docker) → Worker (Docker) → Redis/ChromaDB/PostgreSQL
```

- **Frontend**: Auto-deployed on Vercel from GitHub
- **Backend**: Auto-deployed on EC2 from GitHub Actions
- **Worker**: Automatically processes videos in background
- **All services**: Managed by Docker Compose

---

## Prerequisites Checklist

Before starting, ensure you have:

### On EC2
- [ ] Ubuntu 20.04/22.04 running
- [ ] Docker & Docker Compose installed
- [ ] Nginx installed
- [ ] PostgreSQL running
- [ ] ChromaDB running on port 8001
- [ ] Domain name pointing to EC2 (optional but recommended)
- [ ] SSH access configured

### On GitHub
- [ ] Repository created
- [ ] SSH key for EC2 access

### Services
- [ ] AWS S3 bucket created
- [ ] Google OAuth credentials configured
- [ ] OpenAI API key obtained
- [ ] Gemini API key obtained (optional)

---

## Deployment Steps (30 minutes)

### Step 1: EC2 Setup (10 minutes)

```bash
# SSH to EC2
ssh ubuntu@your-ec2-ip

# Install Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
sudo apt install docker-compose-plugin -y

# Install Nginx
sudo apt install nginx certbot python3-certbot-nginx -y

# Setup SSL (if using domain)
sudo certbot --nginx -d api.yourdomain.com

# Create directory
mkdir -p ~/ai-youtuber-studio/backend/logs
cd ~/ai-youtuber-studio/backend

# Create .env file
nano .env
# Paste your environment variables (see .env.example)
# Save and exit (Ctrl+X, Y, Enter)
```

### Step 2: Configure Nginx (5 minutes)

```bash
# Copy nginx config (you'll need to upload it first or copy from the repo)
sudo nano /etc/nginx/sites-available/ai-youtuber

# Paste the nginx config from deployment/nginx-ai-youtuber.conf
# Replace api.yourdomain.com with your domain
# Save and exit

# Enable site
sudo ln -s /etc/nginx/sites-available/ai-youtuber /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

### Step 3: GitHub Setup (5 minutes)

Go to GitHub → Repository → Settings → Secrets and variables → Actions

Add these secrets:

```
EC2_HOST=your.ec2.ip.address
EC2_SSH_USER=ubuntu
EC2_SSH_KEY=<paste your private SSH key>
EC2_SSH_PORT=22

DATABASE_URL=<your database URL>
REDIS_URL=redis://redis:6379/0
CHROMA_HOST=host.docker.internal
CHROMA_PORT=8001

AWS_ACCESS_KEY_ID=<your key>
AWS_SECRET_ACCESS_KEY=<your secret>
AWS_REGION=us-east-1
S3_BUCKET_NAME=<your bucket>

GOOGLE_CLIENT_ID=<your client id>
GOOGLE_CLIENT_SECRET=<your secret>
GOOGLE_REDIRECT_URI=https://your-frontend.vercel.app

OPENAI_API_KEY=sk-<your key>
GEMINI_API_KEY=<your key>

BACKEND_CORS_ORIGINS=https://your-frontend.vercel.app
```

### Step 4: Deploy Backend (5 minutes)

```bash
# From your local machine
git add .
git commit -m "Setup deployment"
git push origin main

# Watch deployment in GitHub Actions
# Go to: https://github.com/your-username/your-repo/actions
```

That's it! GitHub Actions will:
1. Build Docker images
2. Deploy to EC2
3. Start backend & worker containers
4. Run health checks

### Step 5: Deploy Frontend to Vercel (5 minutes)

```bash
# Go to vercel.com
# Import your repository
# Set environment variable:
VITE_BACKEND_URL=https://api.yourdomain.com

# Click Deploy
```

---

## Verify Deployment

### Check Backend

```bash
# SSH to EC2
ssh ubuntu@your-ec2-ip
cd ~/ai-youtuber-studio/backend

# Check containers
sudo docker compose -f docker-compose.prod.yml ps

# Should show:
# ai-youtuber-backend    running
# ai-youtuber-worker     running
# ai-youtuber-redis      running

# Check logs
sudo docker logs ai-youtuber-backend --tail 50
sudo docker logs ai-youtuber-worker --tail 50

# Test API
curl http://localhost:8000/health
# Should return: {"status":"ok"}

# Test from internet
curl https://api.yourdomain.com/health
```

### Check Worker

```bash
# Check worker status
sudo docker exec -it ai-youtuber-worker celery -A celery_worker inspect active

# Should show worker is running and ready
```

### Check Frontend

Open `https://your-frontend.vercel.app` in browser:
1. Should load the onboarding page
2. Click "Connect YouTube Channel"
3. Complete OAuth flow
4. See dashboard

---

## Test Video Processing

### 1. Sync Videos

In the frontend:
1. Go to Dashboard
2. Click "Sync Videos"
3. Videos appear in Processing Status dashboard

### 2. Watch Processing

1. Go to "Processing Status" in navbar
2. See videos with status:
   - `Queued` → `Downloading Audio` → `Transcribing` → `Indexing` → `Complete`
3. Status updates every 5 seconds automatically

### 3. Verify Completion

```bash
# SSH to EC2
cd ~/ai-youtuber-studio/backend

# Check worker logs
sudo docker logs ai-youtuber-worker --tail 100

# Should see:
# [INFO] Processing video: <video_id>
# [INFO] Downloading audio...
# [INFO] Transcribing...
# [INFO] Indexing in ChromaDB...
# [INFO] Video processing complete
```

**No manual steps required! Everything happens automatically!**

---

## Daily Operations

### View Logs

```bash
# All services
sudo docker compose -f docker-compose.prod.yml logs -f

# Specific service
sudo docker logs ai-youtuber-backend -f
sudo docker logs ai-youtuber-worker -f
```

### Restart Services

```bash
cd ~/ai-youtuber-studio/backend

# Restart all
sudo docker compose -f docker-compose.prod.yml restart

# Restart specific service
sudo docker compose -f docker-compose.prod.yml restart backend
sudo docker compose -f docker-compose.prod.yml restart worker
```

### Update Code

```bash
# Just push to GitHub!
git add .
git commit -m "Update backend"
git push origin main

# GitHub Actions handles the rest automatically
```

### Monitor Resources

```bash
# Container stats
sudo docker stats

# System resources
htop
df -h
```

---

## Common Issues

### Backend Not Starting

```bash
# Check logs
sudo docker logs ai-youtuber-backend --tail 200

# Common fixes:
# 1. Check DATABASE_URL in .env
# 2. Check REDIS_URL in .env
# 3. Restart: sudo docker compose restart backend
```

### Worker Not Processing

```bash
# Check logs
sudo docker logs ai-youtuber-worker --tail 200

# Check worker status
sudo docker exec -it ai-youtuber-worker celery -A celery_worker inspect active

# Restart worker
sudo docker compose restart worker
```

### CORS Errors

```bash
# Check CORS in .env
cat .env | grep CORS

# Update CORS
nano .env
# Add your frontend URL to BACKEND_CORS_ORIGINS

# Restart backend
sudo docker compose restart backend
```

---

## File Structure

After deployment, your EC2 should have:

```
~/ai-youtuber-studio/
└── backend/
    ├── .env                          # Environment variables
    ├── docker-compose.prod.yml       # Production compose file
    ├── Dockerfile                    # Docker image definition
    ├── requirements.txt              # Python dependencies
    ├── app/                          # Application code
    ├── logs/                         # Application logs
    └── celery_worker.py             # Worker configuration
```

---

## Next Steps

1. ✅ **Setup Monitoring**: Consider adding Datadog, New Relic, or CloudWatch
2. ✅ **Setup Backups**: Automate PostgreSQL backups
3. ✅ **Setup Alerts**: Get notified if services go down
4. ✅ **Setup Scaling**: Use AWS Auto Scaling if needed
5. ✅ **Review Security**: Check security groups, SSL config, etc.

---

## Support

- **Deployment Guide**: See `deployment/DEPLOYMENT.md` for detailed documentation
- **Logs**: Check `~/ai-youtuber-studio/backend/logs/`
- **Container Logs**: `sudo docker compose logs -f`

---

## Summary

**What happens when you sync videos:**

1. User clicks "Sync Videos" in frontend
2. Frontend calls `POST /api/channels/{id}/sync-videos`
3. Backend fetches videos from YouTube API
4. Backend automatically queues videos for processing
5. Worker picks up video from queue
6. Worker downloads audio → transcribes → indexes
7. Frontend shows real-time progress
8. User gets notification when complete

**All automatic, zero manual intervention required!** 🚀
