# Docker Setup - Simple & Clean

## 🎯 What's in Docker

The `docker-compose.yml` now runs only these 3 services:

1. **redis** - Message broker (port 6379)
2. **chromadb** - Vector store (port 8001)
3. **worker** - Celery worker for background tasks

**Backend runs locally** for better development experience.

---

## 🚀 Quick Start

```bash
cd ~/Desktop/Projects/ai-youtuber-studio/backend

# Start all Docker services
docker-compose up -d

# Start backend locally (in another terminal)
cd scripts && ./start_backend.sh
```

---

## 📦 Container Names (Simplified)

| Service | Container Name | Port |
|---------|---------------|------|
| Redis | `redis` | 6379 |
| ChromaDB | `chromadb` | 8001 |
| Worker | `worker` | - |

No more `ai-youtuber-` prefix!

---

## ✅ Verify Services

```bash
# Check what's running
docker ps

# Should show:
# - redis
# - chromadb  
# - worker

# Test connections
redis-cli -h localhost -p 6379 ping
curl http://localhost:8001/api/v1/heartbeat
```

---

## 📝 .env Configuration

Update `backend/.env`:

```bash
# For backend running locally
REDIS_URL=redis://localhost:6379/0
CHROMA_HOST=localhost
CHROMA_PORT=8001
```

---

## 🛠️ Common Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# View specific service
docker-compose logs -f redis
docker-compose logs -f chromadb
docker-compose logs -f worker

# Restart a service
docker-compose restart worker

# Check status
docker-compose ps

# Remove containers and volumes
docker-compose down -v
```

---

## 🔄 Start/Stop Individual Services

```bash
# Start only Redis and ChromaDB
docker-compose up -d redis chromadb

# Stop worker only
docker-compose stop worker

# Start worker again
docker-compose start worker
```

---

## 📊 Network

All services are on the `app-network` Docker network, allowing them to communicate using service names:
- Worker → Redis: `redis://redis:6379/0`
- Worker → ChromaDB: `chromadb:8000`

---

## 💾 Data Persistence

Data is stored in Docker volumes:
- `redis-data` - Redis cache and queues
- `chroma-data` - Vector embeddings

View volumes:
```bash
docker volume ls
```

---

## 🎯 Typical Development Workflow

```bash
# 1. Start Docker services (once)
cd ~/Desktop/Projects/ai-youtuber-studio/backend
docker-compose up -d

# 2. Start backend locally (with hot-reload)
cd scripts
./start_backend.sh

# 3. Make code changes
# Backend auto-reloads on changes

# 4. View logs
docker-compose logs -f worker  # Worker logs
tail -f logs/app.log           # Backend logs
```

---

## 🔍 Troubleshooting

### Port conflicts
```bash
# Check what's using ports
lsof -i :6379  # Redis
lsof -i :8001  # ChromaDB

# Stop all Docker services
docker-compose down
```

### Worker not processing tasks
```bash
# Check worker logs
docker-compose logs -f worker

# Restart worker
docker-compose restart worker
```

### Redis connection issues
```bash
# Test Redis
redis-cli -h localhost -p 6379 ping

# Check Redis logs
docker-compose logs redis
```

### ChromaDB connection issues
```bash
# Test ChromaDB
curl http://localhost:8001/api/v1/heartbeat

# Check logs
docker-compose logs chromadb
```

---

## 🎉 Benefits of This Setup

- ✅ **Simple container names** - No `ai-youtuber-` prefix
- ✅ **Backend runs locally** - Hot reload for development
- ✅ **Clean separation** - Services in Docker, code local
- ✅ **Easy debugging** - Backend logs in terminal
- ✅ **Fast iteration** - No Docker rebuild for code changes

