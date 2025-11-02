# Deployment Configuration

This directory contains all the configuration files and documentation needed to deploy the AI YouTuber Studio to production.

## Files Overview

### Configuration Files

| File | Purpose | Location |
|------|---------|----------|
| `nginx-ai-youtuber.conf` | Nginx reverse proxy configuration | Copy to `/etc/nginx/sites-available/` on EC2 |
| `docker-compose.yml` | Development Docker setup | Backend directory |
| `docker-compose.prod.yml` | Production Docker setup | Backend directory |
| `Dockerfile` | Docker image for backend & worker | Backend directory |
| `.dockerignore` | Files to exclude from Docker build | Backend directory |
| `.env.example` | Environment variables template | Backend directory |

### Documentation

| File | Description |
|------|-------------|
| `QUICK_START.md` | 30-minute quick deployment guide |
| `DEPLOYMENT.md` | Comprehensive deployment documentation |
| `README.md` | This file - overview of deployment setup |

### GitHub Actions

| File | Purpose |
|------|---------|
| `.github/workflows/deploy-backend.yml` | Automated deployment to EC2 |

---

## Deployment Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        GitHub Actions                         │
│              (Automatic Deployment on Push)                   │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                      EC2 Instance                             │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Nginx (Port 443) - SSL Termination & Reverse Proxy   │  │
│  └────────────────────┬───────────────────────────────────┘  │
│                       │                                       │
│  ┌────────────────────▼───────────────────────────────────┐  │
│  │           Docker Compose Stack                         │  │
│  │                                                        │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │  │
│  │  │   Backend    │  │    Worker    │  │   Redis    │  │  │
│  │  │   FastAPI    │  │    Celery    │  │  (Queue)   │  │  │
│  │  │  Port 8000   │  │              │  │            │  │  │
│  │  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  │  │
│  │         │                 │                  │         │  │
│  │         └─────────────────┴──────────────────┘         │  │
│  │                           │                            │  │
│  │                           ▼                            │  │
│  │         ┌────────────────────────────────┐            │  │
│  │         │   External Services on Host    │            │  │
│  │         │   - PostgreSQL (Database)      │            │  │
│  │         │   - ChromaDB (Vector Store)    │            │  │
│  │         └────────────────────────────────┘            │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                         ▲
                         │ HTTPS
                         │
┌────────────────────────┴─────────────────────────────────────┐
│                  Vercel (Frontend)                            │
│           Auto-deployed from GitHub                           │
└──────────────────────────────────────────────────────────────┘
```

---

## Key Features

### ✅ Automatic Deployment
- **GitHub Actions** deploys on every push to `main` branch
- **Zero manual steps** required after initial setup
- **Health checks** verify deployment success
- **Rollback capability** if deployment fails

### ✅ Automatic Video Processing
- User syncs videos via frontend
- Backend automatically queues videos for processing
- Worker processes videos in background
- Frontend shows real-time progress
- **No manual intervention needed**

### ✅ Production Ready
- **Docker** containerization for consistency
- **Nginx** reverse proxy with SSL/TLS
- **Health checks** for all services
- **Auto-restart** on failures
- **Logging** configured

### ✅ Scalable
- Worker can handle multiple videos concurrently
- Can add more worker containers if needed
- Redis queue handles load balancing
- Stateless backend supports horizontal scaling

---

## Quick Links

### Getting Started
- 🚀 **[Quick Start Guide](QUICK_START.md)** - 30-minute deployment
- 📚 **[Full Documentation](DEPLOYMENT.md)** - Comprehensive guide

### Configuration
- ⚙️ **Backend Config**: `backend/.env.example`
- 🐳 **Docker Compose**: `backend/docker-compose.prod.yml`
- 🌐 **Nginx Config**: `deployment/nginx-ai-youtuber.conf`
- 🔄 **GitHub Actions**: `.github/workflows/deploy-backend.yml`

---

## Deployment Workflow

### Development
```bash
# Make changes locally
git add .
git commit -m "Your changes"
git push origin main
```

### Automatic Deployment
1. GitHub Actions triggers
2. Code is copied to EC2
3. Docker images are built
4. Containers are restarted
5. Health checks run
6. Nginx reloads
7. Deployment complete! ✅

### Verification
```bash
# Check deployment status
ssh ubuntu@your-ec2-ip
cd ~/ai-youtuber-studio/backend
sudo docker compose -f docker-compose.prod.yml ps
sudo docker compose -f docker-compose.prod.yml logs --tail 50
```

---

## Environment Variables

### Required for Backend
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `CHROMA_HOST`, `CHROMA_PORT` - ChromaDB connection
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME` - S3 storage
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` - YouTube OAuth
- `OPENAI_API_KEY` - For transcription
- `GEMINI_API_KEY` - For AI features
- `BACKEND_CORS_ORIGINS` - Frontend URLs

### Required for GitHub Actions
- `EC2_HOST` - EC2 IP address
- `EC2_SSH_USER` - SSH username (usually `ubuntu`)
- `EC2_SSH_KEY` - Private SSH key for EC2 access
- All backend environment variables (for .env generation)

### Required for Vercel
- `VITE_BACKEND_URL` - Backend API URL (e.g., `https://api.yourdomain.com`)

---

## File Locations on EC2

After deployment:

```
/home/ubuntu/
└── ai-youtuber-studio/
    └── backend/
        ├── .env                          # Environment variables (created by GitHub Actions)
        ├── docker-compose.prod.yml       # Production Docker Compose
        ├── Dockerfile                    # Docker image definition
        ├── requirements.txt              # Python dependencies
        ├── celery_worker.py             # Celery worker config
        ├── app/                          # Application code
        │   ├── main.py                   # FastAPI app
        │   ├── api/                      # API routes
        │   ├── services/                 # Business logic & workers
        │   ├── models/                   # Database models
        │   └── ...
        └── logs/                         # Application logs
            ├── app.log                   # Main application log
            ├── celery_ingest.log        # Worker logs
            └── errors.log                # Error logs

/etc/nginx/
└── sites-available/
    └── ai-youtuber                      # Nginx configuration

/etc/letsencrypt/
└── live/
    └── api.yourdomain.com/              # SSL certificates
        ├── fullchain.pem
        └── privkey.pem
```

---

## Monitoring & Maintenance

### View Logs
```bash
# All services
sudo docker compose -f docker-compose.prod.yml logs -f

# Specific service
sudo docker logs ai-youtuber-backend -f
sudo docker logs ai-youtuber-worker -f
sudo docker logs ai-youtuber-redis -f
```

### Check Container Status
```bash
sudo docker compose -f docker-compose.prod.yml ps
sudo docker stats
```

### Restart Services
```bash
# All services
sudo docker compose -f docker-compose.prod.yml restart

# Specific service
sudo docker compose -f docker-compose.prod.yml restart backend
sudo docker compose -f docker-compose.prod.yml restart worker
```

### Update Environment Variables
```bash
nano ~/ai-youtuber-studio/backend/.env
sudo docker compose -f docker-compose.prod.yml restart
```

---

## Troubleshooting

### Deployment Failed
1. Check GitHub Actions logs
2. Verify GitHub Secrets are set correctly
3. Check SSH key has correct permissions
4. Verify EC2 security groups allow SSH

### Backend Not Responding
1. Check container status: `sudo docker ps`
2. Check logs: `sudo docker logs ai-youtuber-backend`
3. Verify .env file exists and is correct
4. Check database connection

### Worker Not Processing
1. Check worker logs: `sudo docker logs ai-youtuber-worker`
2. Verify Redis connection
3. Check Celery status: `sudo docker exec -it ai-youtuber-worker celery -A celery_worker inspect active`
4. Restart worker: `sudo docker compose restart worker`

### CORS Errors
1. Verify BACKEND_CORS_ORIGINS in .env includes frontend URL
2. Restart backend after updating: `sudo docker compose restart backend`
3. Check nginx logs: `sudo tail -f /var/log/nginx/ai-youtuber-error.log`

---

## Security Checklist

- [ ] SSL certificate installed and auto-renewing
- [ ] Environment variables secured (not in git)
- [ ] EC2 security groups configured (only ports 22, 80, 443 open)
- [ ] Database uses strong password
- [ ] SSH key-based authentication only (no password)
- [ ] Nginx security headers configured
- [ ] Rate limiting enabled in nginx
- [ ] Secrets stored in GitHub Secrets (not in code)
- [ ] .env file has restricted permissions (600)

---

## Performance Optimization

### Backend
- Uses 2 Uvicorn workers in production
- Connection pooling for database
- Redis caching enabled

### Worker
- 4 concurrent worker threads
- Max 100 tasks per child (prevents memory leaks)
- Handles all queues (ingest, transcribe, embedding, generation)

### Nginx
- HTTP/2 enabled
- Gzip compression
- Client max body size: 50MB
- Timeouts: 5 minutes for long requests

---

## Scaling Guide

### Add More Workers
```bash
# Edit docker-compose.prod.yml
nano docker-compose.prod.yml

# Add worker_2 service (copy worker config)
# Change container_name to ai-youtuber-worker-2

# Restart
sudo docker compose -f docker-compose.prod.yml up -d
```

### Increase Worker Concurrency
```bash
# Edit docker-compose.prod.yml
nano docker-compose.prod.yml

# Change worker command:
# --concurrency=4  →  --concurrency=8

# Restart
sudo docker compose -f docker-compose.prod.yml restart worker
```

### Use Managed Services
Consider migrating to:
- **AWS RDS** for PostgreSQL
- **AWS ElastiCache** for Redis
- **AWS S3** for file storage (already using)
- **AWS ECS/Fargate** for container orchestration

---

## Backup Strategy

### Database Backups
```bash
# Create backup script
nano /home/ubuntu/backup-db.sh

#!/bin/bash
pg_dump -U postgres ai_youtuber > /home/ubuntu/backups/ai-youtuber-$(date +%Y%m%d).sql

# Add to crontab (daily at 2 AM)
crontab -e
0 2 * * * /home/ubuntu/backup-db.sh
```

### Environment Backups
```bash
# Backup .env file
cp ~/ai-youtuber-studio/backend/.env ~/ai-youtuber-studio/backend/.env.backup
```

---

## Cost Optimization

### EC2 Instance
- **t3.medium** ($30/month) - Good for small-medium workloads
- **t3.large** ($60/month) - Better for heavy processing
- Use **Reserved Instances** for 40% savings

### S3 Storage
- Use **S3 Lifecycle Policies** to archive old audio files
- Enable **S3 Intelligent Tiering**

### Redis
- Docker Redis is free
- Or use **AWS ElastiCache** (~$13/month for t3.micro)

---

## Support & Resources

- **GitHub Repository**: Your repo URL
- **Documentation**: This directory (`deployment/`)
- **Logs**: `~/ai-youtuber-studio/backend/logs/`
- **Container Logs**: `sudo docker compose logs`

---

## Summary

This deployment setup provides:

✅ **Automatic deployment** via GitHub Actions
✅ **Automatic video processing** via Celery workers
✅ **Production-ready** infrastructure with Docker & Nginx
✅ **Zero manual steps** after initial setup
✅ **Monitoring & logging** built-in
✅ **Scalable** architecture
✅ **Secure** with SSL & proper configuration

**Total setup time: ~30 minutes**
**Maintenance: Push to GitHub, everything else is automatic!**

---

For detailed step-by-step instructions, see:
- **[QUICK_START.md](QUICK_START.md)** - Get started in 30 minutes
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Comprehensive documentation
