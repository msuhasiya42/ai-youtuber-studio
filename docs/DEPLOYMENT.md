# Deployment Guide - AI YouTuber Studio

This guide covers deploying AI YouTuber Studio to production using AWS services.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Quick Start](#quick-start)
3. [Detailed Deployment Steps](#detailed-deployment-steps)
4. [Post-Deployment](#post-deployment)
5. [Scaling & Optimization](#scaling--optimization)
6. [Security Best Practices](#security-best-practices)

---

## Architecture Overview

```
Production Architecture (AWS)

┌─────────────────────────────────────────────────────────────┐
│                      AWS Cloud                               │
│                                                              │
│  ┌────────────────┐     ┌────────────────┐                 │
│  │   CloudFront   │────▶│   S3 (Static)  │  Frontend       │
│  │     (CDN)      │     │    Website     │                  │
│  └────────────────┘     └────────────────┘                  │
│                                                              │
│  ┌────────────────┐     ┌────────────────┐                 │
│  │  API Gateway   │────▶│   Lambda       │  Backend Option │
│  │  / ALB         │     │   Functions    │  (Serverless)   │
│  └────────────────┘     └────────────────┘                  │
│          │                                                   │
│          │              ┌────────────────┐                  │
│          └─────────────▶│   EC2 (FastAPI)│  Backend Option │
│                         │   + Celery     │  (Traditional)  │
│                         └────────────────┘                  │
│                                                              │
│  ┌────────────────┐     ┌────────────────┐                 │
│  │   RDS          │     │   ElastiCache  │                  │
│  │   PostgreSQL   │     │   Redis        │                  │
│  └────────────────┘     └────────────────┘                  │
│                                                              │
│  ┌────────────────┐     ┌────────────────┐                  │
│  │   S3           │     │   EC2/ECS      │                  │
│  │   (Storage)    │     │   ChromaDB     │                  │
│  └────────────────┘     └────────────────┘                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

For users who have already completed the AWS setup in [SETUP_GUIDE.md](SETUP_GUIDE.md):

### Prerequisites Checklist

- [ ] AWS RDS PostgreSQL database running
- [ ] EC2 instance with Redis + ChromaDB running
- [ ] S3 bucket created with IAM permissions
- [ ] Google OAuth credentials configured
- [ ] Gemini/OpenAI API keys obtained
- [ ] SSH tunnels working (for local development)
- [ ] All connection tests passing

### Deploy in 5 Minutes

```bash
# 1. Clone the repository
git clone https://github.com/your-repo/ai-youtuber-studio.git
cd ai-youtuber-studio

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your AWS credentials

# 3. Test connections
./scripts/test_connections.py

# 4. Initialize database
cd backend
source venv/bin/activate
alembic upgrade head

# 5. Start services
cd ..
./scripts/start_all.sh
```

---

## Detailed Deployment Steps

### Step 1: Production Environment Setup

#### 1.1 AWS RDS Configuration

Follow [SETUP_GUIDE.md Section 0️⃣ Step 1](SETUP_GUIDE.md#step-1-setup-aws-rds-postgresql-database) to set up PostgreSQL.

**Production-specific settings:**
```sql
-- After database is created, optimize for production
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Restart RDS instance to apply changes
```

#### 1.2 EC2 Setup for Services

**Option A: Single EC2 Instance (Development/Small Scale)**
- t2.small or t2.medium
- Redis + ChromaDB via Docker (already configured)
- Celery workers on the same instance

**Option B: Multiple EC2 Instances (Production/Large Scale)**
- Dedicated EC2 for Celery workers (t2.medium)
- Dedicated EC2 for ChromaDB (t2.medium with more storage)
- Use ElastiCache for Redis (managed service)

#### 1.3 ElastiCache Redis (Recommended for Production)

**When to use:**
- Production environments
- Need high availability
- Want managed service with automatic failover

**Setup:**
1. Go to ElastiCache console
2. Create Redis cluster:
   - Engine: Redis
   - Node type: cache.t3.micro (start small)
   - Number of replicas: 1 (for HA)
   - Subnet group: Same VPC as EC2/RDS
3. Update REDIS_URL in .env:
   ```
   REDIS_URL=redis://your-cluster.cache.amazonaws.com:6379/0
   ```

### Step 2: Backend Deployment

#### 2.1 EC2 Backend Deployment

**Launch EC2 Instance:**
```bash
# Instance specs:
# - Ubuntu 22.04 LTS
# - t2.medium or larger
# - 30 GB storage
# - Security group: Allow 80, 443, 22
```

**Install dependencies on EC2:**
```bash
# SSH into instance
ssh -i your-key.pem ubuntu@ec2-instance-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install system dependencies
sudo apt install -y ffmpeg redis-tools postgresql-client

# Install nginx (for reverse proxy)
sudo apt install -y nginx

# Install supervisord (for process management)
sudo apt install -y supervisor

# Clone repository
git clone https://github.com/your-repo/ai-youtuber-studio.git
cd ai-youtuber-studio/backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install gunicorn for production
pip install gunicorn uvicorn[standard]
```

**Configure environment:**
```bash
# Create .env file
nano .env
# Paste your production environment variables
```

**Run database migrations:**
```bash
alembic upgrade head
```

#### 2.2 Supervisor Configuration

Create `/etc/supervisor/conf.d/ai-youtuber-backend.conf`:

```ini
[program:ai-youtuber-backend]
command=/home/ubuntu/ai-youtuber-studio/backend/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
directory=/home/ubuntu/ai-youtuber-studio/backend
user=ubuntu
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/ai-youtuber-backend.log
environment=PATH="/home/ubuntu/ai-youtuber-studio/backend/venv/bin"
```

Create `/etc/supervisor/conf.d/ai-youtuber-worker.conf`:

```ini
[program:ai-youtuber-worker]
command=/home/ubuntu/ai-youtuber-studio/backend/venv/bin/celery -A celery_worker.app worker --loglevel=INFO --concurrency=4
directory=/home/ubuntu/ai-youtuber-studio/backend
user=ubuntu
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/ai-youtuber-worker.log
environment=PATH="/home/ubuntu/ai-youtuber-studio/backend/venv/bin"
```

**Start services:**
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start ai-youtuber-backend
sudo supervisorctl start ai-youtuber-worker
```

#### 2.3 Nginx Reverse Proxy

Create `/etc/nginx/sites-available/ai-youtuber`:

```nginx
server {
    listen 80;
    server_name api.your-domain.com;  # Replace with your domain

    # Increase timeouts for long-running requests
    proxy_read_timeout 300;
    proxy_connect_timeout 300;
    proxy_send_timeout 300;

    # Increase body size for file uploads
    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

**Enable site and restart nginx:**
```bash
sudo ln -s /etc/nginx/sites-available/ai-youtuber /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 2.4 SSL Certificate (Let's Encrypt)

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d api.your-domain.com

# Certbot will auto-configure nginx for HTTPS
# Certificates auto-renew via cron
```

### Step 3: Frontend Deployment

#### 3.1 Build Frontend

```bash
# On your local machine
cd frontend

# Update .env for production
cat > .env <<EOF
VITE_BACKEND_URL=https://api.your-domain.com
VITE_GEMINI_API_KEY=your_gemini_key
EOF

# Build for production
npm run build

# This creates a 'dist' directory with static files
```

#### 3.2 Deploy to S3 + CloudFront

```bash
# Install AWS CLI
pip install awscli

# Configure AWS
aws configure

# Create S3 bucket for static hosting
aws s3 mb s3://your-app.com --region us-east-1

# Configure bucket for static website hosting
aws s3 website s3://your-app.com --index-document index.html --error-document index.html

# Upload built files
aws s3 sync dist/ s3://your-app.com --delete

# Make files public
aws s3 cp s3://your-app.com s3://your-app.com --recursive --acl public-read
```

**Create CloudFront distribution:**
1. Go to CloudFront console
2. Create distribution:
   - Origin: your-app.com.s3.amazonaws.com
   - Origin protocol: HTTP only
   - Viewer protocol: Redirect HTTP to HTTPS
   - Price class: Use all edge locations
   - Alternate domain names: your-app.com, www.your-app.com
   - SSL certificate: Request certificate via ACM
   - Default root object: index.html
3. Wait for distribution to deploy (~15 minutes)

**Update DNS:**
- Add CNAME record: `your-app.com` → CloudFront distribution URL
- Add CNAME record: `www.your-app.com` → CloudFront distribution URL

---

## Post-Deployment

### Verify Deployment

```bash
# Test backend API
curl https://api.your-domain.com/health

# Expected: {"status": "healthy"}

# Test frontend
curl https://your-app.com

# Should return HTML
```

### Monitor Services

**CloudWatch Logs:**
- Set up log groups for backend, workers, and nginx
- Create alarms for errors and high CPU usage

**Monitoring script:**
```bash
# Check all services
./scripts/test_connections.py

# Check supervisor status
sudo supervisorctl status

# Check nginx
sudo systemctl status nginx

# Check logs
tail -f /var/log/ai-youtuber-backend.log
tail -f /var/log/ai-youtuber-worker.log
```

### Backup Strategy

**Database backups:**
- RDS automated backups (enabled by default)
- Manual snapshots before major changes

**S3 versioning:**
```bash
aws s3api put-bucket-versioning \
    --bucket ai-youtube-data \
    --versioning-configuration Status=Enabled
```

**Configuration backups:**
```bash
# Backup .env and supervisor configs
tar -czf backup-$(date +%Y%m%d).tar.gz \
    backend/.env \
    /etc/supervisor/conf.d/ai-youtuber-*.conf \
    /etc/nginx/sites-available/ai-youtuber
```

---

## Scaling & Optimization

### Horizontal Scaling

**Add more Celery workers:**
```bash
# On a new EC2 instance
# Install same dependencies
# Copy .env file
# Start only the worker (not the backend)
sudo supervisorctl start ai-youtuber-worker
```

**Load balancer for backend:**
1. Create Application Load Balancer (ALB)
2. Add EC2 instances to target group
3. Update CloudFront origin to ALB
4. Enable health checks

### Performance Optimization

**Database indexing:**
```sql
-- Add indexes for common queries
CREATE INDEX idx_videos_channel_id ON videos(channel_id);
CREATE INDEX idx_videos_published_at ON videos(published_at);
CREATE INDEX idx_transcripts_video_id ON transcripts(video_id);
```

**Redis caching:**
- Cache YouTube API responses (TTL: 1 hour)
- Cache channel data (TTL: 5 minutes)
- Cache generated scripts (TTL: 24 hours)

**S3 lifecycle policies:**
```bash
# Move old audio files to Glacier after 30 days
# Delete temporary files after 7 days
```

---

## Security Best Practices

### Environment Variables

**Use AWS Secrets Manager:**
```python
# backend/app/core/config.py
import boto3
from botocore.exceptions import ClientError

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-east-1')
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except ClientError as e:
        raise e

# In production, load from Secrets Manager
if os.getenv('ENV') == 'production':
    OPENAI_API_KEY = get_secret('ai-youtuber/openai-key')
else:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
```

### Security Group Rules

**RDS Security Group:**
```
Inbound:
- PostgreSQL (5432) from Backend EC2 security group only
```

**Backend EC2 Security Group:**
```
Inbound:
- HTTP (80) from ALB only
- HTTPS (443) from ALB only
- SSH (22) from your IP only
```

**Redis/ChromaDB EC2 Security Group:**
```
Inbound:
- 6379 (Redis) from Backend EC2 security group only
- 8001 (ChromaDB) from Backend EC2 security group only
- SSH (22) from your IP only
```

### IAM Policies

Use least-privilege IAM roles:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::ai-youtube-data/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::ai-youtube-data"
    }
  ]
}
```

### Rate Limiting

Add rate limiting to nginx:
```nginx
# In http block
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

# In server block
location / {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://127.0.0.1:8000;
}
```

---

## Cost Optimization

### Monthly Cost Breakdown

| Service | Configuration | Estimated Cost |
|---------|--------------|----------------|
| RDS db.t3.micro | PostgreSQL | $15-20/mo |
| EC2 t2.medium (backend) | 1 instance | $30-35/mo |
| EC2 t2.micro (services) | Redis+ChromaDB | $0 (free tier) |
| S3 Storage | 20 GB | $0.46/mo |
| S3 Requests | 100K GET, 10K PUT | $0.45/mo |
| CloudFront | 10 GB transfer | $0.85/mo |
| ElastiCache (optional) | cache.t3.micro | $12/mo |
| **Total** | | **~$47-70/mo** |

### Cost Reduction Tips

1. **Use EC2 Reserved Instances** - Save 40% with 1-year commitment
2. **Use S3 Intelligent-Tiering** - Auto-move cold data to cheaper storage
3. **Enable RDS stop/start** - Stop dev instances during off-hours
4. **Use CloudFront caching** - Reduce S3 GET requests by 90%
5. **Optimize Celery workers** - Scale down during low-traffic hours

---

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.

---

## Support

For deployment issues:
1. Check logs: `/var/log/ai-youtuber-*.log`
2. Run connection tests: `./scripts/test_connections.py`
3. Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
4. Open an issue on GitHub

---

**Last Updated:** 2025-01-08
