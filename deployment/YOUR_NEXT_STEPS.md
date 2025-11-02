# 🚀 Your Next Steps - Complete Deployment Checklist

## ✅ What I've Done For You

I've completed the following from your local machine:

1. ✅ Created all deployment infrastructure files:
   - GitHub Actions workflow (`.github/workflows/deploy-backend.yml`)
   - Docker configurations (`docker-compose.yml`, `docker-compose.prod.yml`)
   - Nginx configuration (`deployment/nginx-ai-youtuber.conf`)
   - Comprehensive documentation (3 guides in `deployment/` folder)
   - Updated `.env.example` with Docker settings

2. ✅ Committed everything to git (commit: 907e7a8)

3. ✅ Ready for you to push to GitHub

---

## 📋 What You Need To Do Now

### Step 1: Push to GitHub (1 minute)

```bash
# You're in: /Users/mayursuhasiya/Desktop/Projects/ai-youtuber-studio

# Push the commit to GitHub
git push origin main
```

**What this does:** Uploads all deployment files to GitHub (but doesn't deploy yet - we need to set up secrets first)

---

### Step 2: Setup GitHub Secrets (10 minutes)

**Go to:** `https://github.com/YOUR_USERNAME/ai-youtuber-studio/settings/secrets/actions`

Click **"New repository secret"** and add each of these:

#### EC2 Connection Secrets

```
Name: EC2_HOST
Value: YOUR_EC2_PUBLIC_IP (e.g., 54.123.456.789)

Name: EC2_SSH_USER
Value: ubuntu

Name: EC2_SSH_KEY
Value: (paste entire content of your .pem file)
       -----BEGIN RSA PRIVATE KEY-----
       ... all lines ...
       -----END RSA PRIVATE KEY-----

Name: EC2_SSH_PORT
Value: 22
```

#### Database & Services Secrets

```
Name: DATABASE_URL
Value: postgresql://USER:PASSWORD@localhost:5432/DBNAME
       (your PostgreSQL connection string on EC2)

Name: REDIS_URL
Value: redis://redis:6379/0

Name: CHROMA_HOST
Value: host.docker.internal

Name: CHROMA_PORT
Value: 8001
```

#### AWS S3 Secrets

```
Name: AWS_ACCESS_KEY_ID
Value: (your AWS access key)

Name: AWS_SECRET_ACCESS_KEY
Value: (your AWS secret key)

Name: AWS_REGION
Value: us-east-1 (or your region)

Name: S3_BUCKET_NAME
Value: (your S3 bucket name)
```

#### Google OAuth Secrets

```
Name: GOOGLE_CLIENT_ID
Value: (your Google OAuth client ID)

Name: GOOGLE_CLIENT_SECRET
Value: (your Google OAuth client secret)

Name: GOOGLE_REDIRECT_URI
Value: http://YOUR_EC2_IP (or Vercel URL later)
```

#### AI API Keys

```
Name: OPENAI_API_KEY
Value: sk-... (your OpenAI API key)

Name: GEMINI_API_KEY
Value: (your Gemini API key - optional)
```

#### CORS Configuration

```
Name: BACKEND_CORS_ORIGINS
Value: http://YOUR_EC2_IP,http://localhost:3000
       (will add Vercel URL later)
```

---

### Step 3: Setup EC2 (15 minutes)

**SSH to your EC2:**

```bash
ssh -i /path/to/your-key.pem ubuntu@YOUR_EC2_IP
```

**Install Docker & Docker Compose:**

```bash
# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose plugin
sudo apt update
sudo apt install docker-compose-plugin -y

# Verify
docker --version
docker compose version
```

**Install Nginx:**

```bash
sudo apt install nginx -y
```

**Configure Nginx for HTTP (no SSL for now):**

```bash
# Create nginx config
sudo tee /etc/nginx/sites-available/ai-youtuber <<'EOF'
upstream backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name _;

    client_max_body_size 50M;

    location / {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/ai-youtuber /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default || true

# Test and reload
sudo nginx -t
sudo systemctl restart nginx
```

**Create deployment directory:**

```bash
mkdir -p ~/ai-youtuber-studio/backend/logs
cd ~/ai-youtuber-studio/backend
```

**Verify existing services are running:**

```bash
# Check ChromaDB
curl http://localhost:8001/api/v1/heartbeat
# Should return: {"nanosecond heartbeat": ...}

# Check PostgreSQL
sudo systemctl status postgresql
# Should show: active (running)
```

**Exit EC2:**

```bash
exit
```

---

### Step 4: Trigger First Deployment (2 minutes)

Now that GitHub Secrets are set up, trigger the deployment:

**Option A: Make a small change and push**

```bash
# On your local machine
cd /Users/mayursuhasiya/Desktop/Projects/ai-youtuber-studio

# Make a small change (or just commit empty)
git commit --allow-empty -m "Trigger deployment"
git push origin main
```

**Option B: Manually trigger workflow**

1. Go to: `https://github.com/YOUR_USERNAME/ai-youtuber-studio/actions`
2. Click on "Deploy Backend to EC2" workflow
3. Click "Run workflow" button
4. Select branch: `main`
5. Click green "Run workflow" button

**Watch the deployment:**

1. Go to Actions tab: `https://github.com/YOUR_USERNAME/ai-youtuber-studio/actions`
2. Click on the running workflow
3. Watch the logs in real-time
4. Wait for green checkmark (~5 minutes)

---

### Step 5: Verify Backend Deployment (5 minutes)

**SSH to EC2:**

```bash
ssh -i /path/to/your-key.pem ubuntu@YOUR_EC2_IP
cd ~/ai-youtuber-studio/backend
```

**Check containers:**

```bash
sudo docker compose -f docker-compose.prod.yml ps
```

**Expected output:**

```
NAME                      STATUS              PORTS
ai-youtuber-backend       Up 2 minutes        0.0.0.0:8000->8000/tcp
ai-youtuber-worker        Up 2 minutes
ai-youtuber-redis         Up 2 minutes        0.0.0.0:6379->6379/tcp
```

**Check logs:**

```bash
# Backend logs
sudo docker logs ai-youtuber-backend --tail 50

# Worker logs
sudo docker logs ai-youtuber-worker --tail 50

# Should see no errors
```

**Test API:**

```bash
# Test from inside EC2
curl http://localhost:8000/health
# Should return: {"status":"ok"}

# Test from outside EC2 (from your local machine, open new terminal)
curl http://YOUR_EC2_IP/health
# Should also return: {"status":"ok"}
```

**Check worker status:**

```bash
sudo docker exec -it ai-youtuber-worker celery -A celery_worker inspect active
# Should show: worker is ready, no active tasks
```

---

### Step 6: Deploy Frontend to Vercel (10 minutes)

**Go to Vercel:**

1. Visit: `https://vercel.com`
2. Sign in with GitHub
3. Click **"Add New Project"**
4. **Import** your GitHub repository: `ai-youtuber-studio`

**Configure Project:**

- **Framework Preset:** Vite
- **Root Directory:** `frontend` (if your frontend is in a subdirectory)
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Install Command:** `npm install`

**Add Environment Variable:**

Click "Environment Variables" and add:

```
Name: VITE_BACKEND_URL
Value: http://YOUR_EC2_PUBLIC_IP
```

**Click "Deploy"**

Wait ~2-3 minutes for build to complete.

**Get your Vercel URL:**

After deployment, you'll see: `https://ai-youtuber-studio-xxx.vercel.app`

Copy this URL!

---

### Step 7: Update CORS (5 minutes)

Now that you have your Vercel URL, update CORS:

**SSH to EC2:**

```bash
ssh -i /path/to/your-key.pem ubuntu@YOUR_EC2_IP
cd ~/ai-youtuber-studio/backend
```

**Edit .env file:**

```bash
nano .env
```

**Find the line:**

```
BACKEND_CORS_ORIGINS=http://YOUR_EC2_IP,http://localhost:3000
```

**Change to:**

```
BACKEND_CORS_ORIGINS=http://YOUR_EC2_IP,https://YOUR-APP.vercel.app,http://localhost:3000
```

**Save:** `Ctrl+X`, then `Y`, then `Enter`

**Restart backend:**

```bash
sudo docker compose -f docker-compose.prod.yml restart backend
```

**Also update GitHub Secret:**

1. Go to: `https://github.com/YOUR_USERNAME/ai-youtuber-studio/settings/secrets/actions`
2. Edit `BACKEND_CORS_ORIGINS` secret
3. Change value to: `http://YOUR_EC2_IP,https://YOUR-APP.vercel.app,http://localhost:3000`
4. Save

---

### Step 8: Test Complete System (10 minutes)

**Test Frontend:**

1. Open: `https://YOUR-APP.vercel.app`
2. Should see "AI YouTuber Studio" onboarding page
3. Click **"Connect YouTube Channel"**
4. Should redirect to Google OAuth
5. Sign in with your Google account
6. Should redirect back and show Dashboard

**Test Video Sync:**

1. In Dashboard, click **"Sync Videos"** button
2. Wait for videos to sync (~30 seconds)
3. Should see success message

**Test Video Processing:**

1. Click **"Processing Status"** in navbar
2. Should see your videos listed
3. Watch status change in real-time:
   - `Queued` → `Downloading Audio` → `Transcribing` → `Indexing` → `Complete`
4. Status updates every 5 seconds automatically

**Test Performance Analyzer:**

1. Click **"Performance Analyzer"** in navbar
2. Should see performance analysis of your videos
3. Keywords, themes, recommendations displayed

**Verify Worker (SSH to EC2):**

```bash
sudo docker logs ai-youtuber-worker -f
```

**You should see logs like:**

```
[INFO] Processing video: xyz
[INFO] Downloading audio from YouTube...
[INFO] Audio downloaded successfully
[INFO] Transcribing audio with Whisper...
[INFO] Transcription complete
[INFO] Indexing in ChromaDB...
[INFO] Video processing complete!
```

**Press Ctrl+C to exit logs**

---

## 🎉 Success Criteria

You'll know everything is working when:

- ✅ GitHub Actions shows green checkmark
- ✅ 3 containers running on EC2 (backend, worker, redis)
- ✅ `curl http://YOUR_EC2_IP/health` returns `{"status":"ok"}`
- ✅ Frontend loads on Vercel
- ✅ Can sign in with Google
- ✅ Videos sync successfully
- ✅ Processing Status shows videos
- ✅ Status updates automatically
- ✅ Videos reach "Complete" status
- ✅ Worker logs show processing activity

---

## 🔄 Daily Workflow (After Setup)

### Update Backend Code

```bash
# Edit backend code locally
git add .
git commit -m "Update feature"
git push origin main
# GitHub Actions deploys automatically!
```

### Update Frontend Code

```bash
# Edit frontend code locally
git add .
git commit -m "Update UI"
git push origin main
# Vercel deploys automatically!
```

### Monitor Services

```bash
# SSH to EC2
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
cd ~/ai-youtuber-studio/backend

# View logs
sudo docker compose -f docker-compose.prod.yml logs -f

# Check status
sudo docker compose -f docker-compose.prod.yml ps

# Restart services
sudo docker compose -f docker-compose.prod.yml restart
```

---

## 🆘 Troubleshooting Quick Reference

### GitHub Actions Fails

```bash
# Check Actions logs on GitHub
# Common issue: SSH key incorrect
# Fix: Copy entire .pem file content including BEGIN/END lines
```

### Backend Not Responding

```bash
ssh ubuntu@YOUR_EC2_IP
cd ~/ai-youtuber-studio/backend

# Check logs
sudo docker logs ai-youtuber-backend --tail 100

# Check if .env exists
cat .env | head -5

# Restart
sudo docker compose -f docker-compose.prod.yml restart backend
```

### Worker Not Processing

```bash
# Check worker logs
sudo docker logs ai-youtuber-worker --tail 100

# Check worker status
sudo docker exec -it ai-youtuber-worker celery -A celery_worker inspect active

# Restart worker
sudo docker compose -f docker-compose.prod.yml restart worker
```

### CORS Errors

```bash
# Update CORS in .env
nano ~/ai-youtuber-studio/backend/.env
# Add your Vercel URL to BACKEND_CORS_ORIGINS

# Restart backend
sudo docker compose restart backend
```

---

## 📚 Documentation Reference

All detailed documentation is in the `deployment/` folder:

- **[QUICK_START.md](QUICK_START.md)** - 30-minute quick start guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Comprehensive deployment guide with troubleshooting
- **[README.md](README.md)** - Architecture overview and reference

---

## ⏱️ Estimated Time

- Step 1 (Push to GitHub): 1 minute
- Step 2 (GitHub Secrets): 10 minutes
- Step 3 (EC2 Setup): 15 minutes
- Step 4 (First Deployment): 2 minutes
- Step 5 (Verify Backend): 5 minutes
- Step 6 (Deploy Frontend): 10 minutes
- Step 7 (Update CORS): 5 minutes
- Step 8 (Test System): 10 minutes

**Total: ~1 hour**

---

## 🎯 Summary

**What's automated:**
- ✅ Backend deployment (push to GitHub)
- ✅ Frontend deployment (push to GitHub)
- ✅ Video processing (worker handles automatically)
- ✅ Health checks
- ✅ Container restarts on failure

**What you do:**
- Push code to GitHub
- That's it!

Everything else is automatic. 🚀

---

## 📞 Need Help?

If you get stuck:

1. Check the detailed guides in `deployment/` folder
2. Check container logs: `sudo docker compose logs -f`
3. Check GitHub Actions logs
4. Verify all secrets are set correctly
5. Ensure EC2 security groups allow ports 22, 80

---

**Good luck! 🎉**

Start with Step 1 - just push to GitHub! Then follow each step in order.
