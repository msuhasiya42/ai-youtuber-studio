# Troubleshooting Guide - AI YouTuber Studio

Common issues and their solutions.

## Table of Contents

1. [Connection Issues](#connection-issues)
2. [Database Issues](#database-issues)
3. [AWS S3 Issues](#aws-s3-issues)
4. [API Issues](#api-issues)
5. [Worker/Celery Issues](#workercelery-issues)
6. [Frontend Issues](#frontend-issues)
7. [Performance Issues](#performance-issues)

---

## Connection Issues

### SSH Tunnel Connection Refused

**Symptoms:**
```
ssh: connect to host <EC2-IP> port 22: Connection refused
```

**Solutions:**
1. Check EC2 instance is running:
   ```bash
   aws ec2 describe-instances --instance-ids i-xxxxx
   ```

2. Verify security group allows SSH (port 22) from your IP:
   - Go to EC2 console → Security Groups
   - Check inbound rules for SSH from your current IP

3. Verify PEM file permissions:
   ```bash
   chmod 400 ~/Desktop/AWS/ai-youtuber-studio-key.pem
   ```

4. Get current EC2 public IP (it may have changed):
   ```bash
   aws ec2 describe-instances --instance-ids i-xxxxx --query 'Reservations[0].Instances[0].PublicIpAddress'
   ```

### Redis Connection Failed

**Symptoms:**
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solutions:**

1. **Check if SSH tunnel is running:**
   ```bash
   ps aux | grep "ssh.*6379"
   ```

   If not running:
   ```bash
   ./scripts/start_tunnels.sh
   ```

2. **Test Redis directly:**
   ```bash
   redis-cli -h 127.0.0.1 -p 6379 ping
   ```

   Expected: `PONG`

3. **Check Redis on EC2:**
   ```bash
   ssh -i ~/Desktop/AWS/ai-youtuber-studio-key.pem ubuntu@<EC2-IP>
   docker-compose ps
   docker-compose logs redis
   ```

4. **Restart Redis on EC2:**
   ```bash
   ssh -i ~/Desktop/AWS/ai-youtuber-studio-key.pem ubuntu@<EC2-IP>
   docker-compose restart redis
   ```

### ChromaDB Connection Failed

**Symptoms:**
```
requests.exceptions.ConnectionError: Cannot connect to ChromaDB
```

**Solutions:**

1. **Check if SSH tunnel is running:**
   ```bash
   lsof -i :8001
   ```

2. **Test ChromaDB directly:**
   ```bash
   curl http://127.0.0.1:8001/api/v1/heartbeat
   ```

   Expected: `{"nanosecond heartbeat": ...}`

3. **Check ChromaDB on EC2:**
   ```bash
   ssh -i ~/Desktop/AWS/ai-youtuber-studio-key.pem ubuntu@<EC2-IP>
   docker-compose logs chroma
   ```

4. **Restart ChromaDB on EC2:**
   ```bash
   ssh -i ~/Desktop/AWS/ai-youtuber-studio-key.pem ubuntu@<EC2-IP>
   docker-compose restart chroma
   ```

---

## Database Issues

### PostgreSQL Connection Failed

**Symptoms:**
```
psycopg2.OperationalError: could not connect to server
```

**Solutions:**

1. **Check DATABASE_URL format:**
   ```bash
   # Correct format:
   DATABASE_URL=postgresql://username:password@host:5432/database

   # Common mistakes:
   # - Missing port :5432
   # - Special characters in password not URL-encoded
   # - Wrong database name
   ```

2. **URL-encode password with special characters:**
   ```python
   from urllib.parse import quote_plus
   password = "Mvsmj143$"
   encoded = quote_plus(password)
   print(f"postgresql://postgres:{encoded}@host:5432/db")
   ```

3. **Check RDS security group:**
   - Ensure inbound rule allows PostgreSQL (5432) from your IP
   - Or from EC2 security group if running backend on EC2

4. **Verify RDS is running:**
   ```bash
   aws rds describe-db-instances --db-instance-identifier ai-youtuber-studio-db
   ```

5. **Test connection manually:**
   ```bash
   psql "postgresql://postgres:PASSWORD@RDS-ENDPOINT:5432/ai_youtuber_studio"
   ```

### Database Migration Failed

**Symptoms:**
```
alembic.util.exc.CommandError: Can't locate revision
```

**Solutions:**

1. **Check current migration status:**
   ```bash
   cd backend
   alembic current
   ```

2. **Reset migrations (⚠️ WARNING: Deletes all data):**
   ```bash
   # Downgrade to base
   alembic downgrade base

   # Upgrade to latest
   alembic upgrade head
   ```

3. **Initialize database if new:**
   ```bash
   python init_db.py
   ```

4. **Check for migration conflicts:**
   ```bash
   alembic history
   alembic branches
   ```

---

## AWS S3 Issues

### S3 Access Denied

**Symptoms:**
```
botocore.exceptions.ClientError: An error occurred (AccessDenied)
```

**Solutions:**

1. **Check AWS credentials are set:**
   ```bash
   grep AWS_ backend/.env
   ```

   Should show:
   ```
   AWS_ACCESS_KEY_ID=AKIA...
   AWS_SECRET_ACCESS_KEY=...
   AWS_S3_BUCKET=ai-youtube-data
   ```

2. **Verify IAM permissions:**
   - Go to IAM console
   - Find your user
   - Check attached policies include S3 access

3. **Test AWS credentials:**
   ```bash
   aws sts get-caller-identity
   ```

   Should return your user info.

4. **Test S3 bucket access:**
   ```bash
   aws s3 ls s3://ai-youtube-data/
   ```

5. **Check bucket exists:**
   ```bash
   aws s3 ls | grep ai-youtube-data
   ```

### S3 Bucket Not Found

**Symptoms:**
```
botocore.exceptions.ClientError: The specified bucket does not exist
```

**Solutions:**

1. **Verify bucket name in .env:**
   ```bash
   grep AWS_S3_BUCKET backend/.env
   ```

   Must match actual bucket name (case-sensitive).

2. **List your buckets:**
   ```bash
   aws s3 ls
   ```

3. **Create bucket if missing:**
   ```bash
   aws s3 mb s3://ai-youtube-data --region us-east-1
   ```

4. **Check bucket region matches AWS_REGION:**
   ```bash
   aws s3api get-bucket-location --bucket ai-youtube-data
   ```

---

## API Issues

### OpenAI API Key Invalid

**Symptoms:**
```
openai.error.AuthenticationError: Incorrect API key provided
```

**Solutions:**

1. **Check API key format:**
   - OpenAI keys start with `sk-proj-` or `sk-`
   - No spaces or quotes around the key

2. **Verify key is active:**
   - Go to https://platform.openai.com/api-keys
   - Check if key is active (not revoked)

3. **Check billing:**
   - Go to https://platform.openai.com/account/billing
   - Ensure you have credits or valid payment method

4. **Regenerate key:**
   - Create new key on OpenAI platform
   - Update .env file
   - Restart backend

### Gemini API Rate Limit

**Symptoms:**
```
google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded
```

**Solutions:**

1. **Check free tier limits:**
   - Gemini Flash: 15 requests/minute
   - Gemini Pro: 60 requests/day (free tier)

2. **Implement exponential backoff:**
   ```python
   import time
   from google.api_core import retry

   @retry.Retry(deadline=60)
   def call_gemini():
       # Your Gemini API call
       pass
   ```

3. **Upgrade to paid tier:**
   - Go to Google AI Studio
   - Enable billing

4. **Switch to OpenAI temporarily:**
   ```bash
   # In .env
   LLM_PROVIDER=openai
   ```

### YouTube API Quota Exceeded

**Symptoms:**
```
googleapiclient.errors.HttpError: 403 quotaExceeded
```

**Solutions:**

1. **Check quota usage:**
   - Go to: https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas
   - Daily quota: 10,000 units (default)

2. **Reduce API calls:**
   - Implement caching (1-hour TTL for channel data)
   - Batch requests when possible
   - Use webhooks instead of polling

3. **Request quota increase:**
   - Go to: https://support.google.com/youtube/contact/yt_api_form
   - Explain use case
   - May take 1-2 weeks

---

## Worker/Celery Issues

### Worker Not Processing Tasks

**Symptoms:**
```
Tasks stuck in PENDING state
```

**Solutions:**

1. **Check worker is running:**
   ```bash
   ps aux | grep celery
   ```

2. **Check worker logs:**
   ```bash
   # If using supervisor
   sudo tail -f /var/log/ai-youtuber-worker.log

   # If running manually
   celery -A celery_worker.app worker --loglevel=DEBUG
   ```

3. **Check Redis connection:**
   ```bash
   redis-cli -u "$REDIS_URL" ping
   ```

4. **Purge stuck tasks:**
   ```bash
   celery -A celery_worker.app purge
   ```

5. **Restart worker:**
   ```bash
   # Kill existing workers
   pkill -f "celery.*worker"

   # Start fresh
   ./scripts/start_worker.sh
   ```

### Celery Import Error

**Symptoms:**
```
AttributeError: module 'app' has no attribute 'task'
```

**Solutions:**

1. **This was fixed in the codebase!** Update your code:
   ```bash
   git pull origin main
   ```

2. **Verify worker files use `celery_app`:**
   ```bash
   grep "from celery_worker import app" backend/app/services/*_worker.py
   ```

   Should show:
   ```python
   from celery_worker import app as celery_app
   ```

3. **Reinstall dependencies:**
   ```bash
   cd backend
   pip install --upgrade -r requirements.txt
   ```

---

## Frontend Issues

### Backend API Not Reachable

**Symptoms:**
```
Failed to fetch
net::ERR_CONNECTION_REFUSED
```

**Solutions:**

1. **Check VITE_BACKEND_URL in frontend/.env:**
   ```bash
   cat frontend/.env
   ```

   Should be:
   ```
   VITE_BACKEND_URL=http://localhost:8000
   ```

2. **Verify backend is running:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Check CORS settings:**
   ```bash
   grep BACKEND_CORS_ORIGINS backend/.env
   ```

   Should include frontend URL:
   ```
   BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173
   ```

4. **Restart backend after .env changes:**
   ```bash
   ./scripts/start_backend.sh
   ```

### Google OAuth Redirect Error

**Symptoms:**
```
redirect_uri_mismatch
```

**Solutions:**

1. **Check redirect URI in .env:**
   ```bash
   grep GOOGLE_OAUTH_REDIRECT_URI backend/.env
   ```

2. **Verify in Google Console:**
   - Go to: https://console.cloud.google.com/apis/credentials
   - Select your OAuth client
   - Check "Authorized redirect URIs" includes:
     - `http://localhost:8000/api/auth/oauth/google/callback`

3. **Ensure exact match:**
   - No trailing slash
   - Correct protocol (http vs https)
   - Correct port

---

## Performance Issues

### Slow Database Queries

**Solutions:**

1. **Add indexes:**
   ```sql
   CREATE INDEX idx_videos_channel_id ON videos(channel_id);
   CREATE INDEX idx_videos_published_at ON videos(published_at);
   ```

2. **Analyze slow queries:**
   ```sql
   EXPLAIN ANALYZE SELECT * FROM videos WHERE channel_id = 1;
   ```

3. **Enable query logging:**
   ```sql
   ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1s
   ```

### High Memory Usage

**Solutions:**

1. **Check Celery worker concurrency:**
   ```bash
   # Reduce concurrency in start_worker.sh
   celery -A celery_worker.app worker --concurrency=2
   ```

2. **Monitor memory:**
   ```bash
   # On Mac
   top -o MEM

   # On Linux
   htop
   ```

3. **Increase EC2 instance size** if consistently high

### Slow S3 Uploads

**Solutions:**

1. **Use multipart upload for large files:**
   ```python
   # Already implemented in storage_client.py
   # For files > 100MB
   ```

2. **Check network bandwidth:**
   ```bash
   speedtest-cli
   ```

3. **Use S3 Transfer Acceleration:**
   ```python
   s3_client = boto3.client(
       's3',
       config=Config(s3={'use_accelerate_endpoint': True})
   )
   ```

---

## Quick Diagnostic Commands

```bash
# Full system check
./scripts/test_connections.py

# Check all environment variables
cd backend && cat .env | grep -v "^#" | grep -v "^$"

# Check all running processes
ps aux | grep -E "python|celery|redis|ssh"

# Check all open ports
lsof -i -P -n | grep LISTEN

# Check disk space
df -h

# Check memory
free -h  # Linux
vm_stat  # Mac

# Check logs
tail -f /var/log/ai-youtuber-*.log  # Production
tail -f backend/logs/*.log          # Development
```

---

## Getting Help

If you're still stuck after trying these solutions:

1. **Check GitHub Issues:**
   - https://github.com/your-repo/ai-youtuber-studio/issues

2. **Create a new issue with:**
   - Error message (full stack trace)
   - Steps to reproduce
   - Output of `./scripts/test_connections.py`
   - OS and Python version
   - Relevant log files

3. **Include diagnostic info:**
   ```bash
   python --version
   pip freeze > requirements-actual.txt
   env | grep -E "AWS|REDIS|CHROMA|DATABASE" | sed 's/=.*/=***/'
   ```

---

**Last Updated:** 2025-01-08
