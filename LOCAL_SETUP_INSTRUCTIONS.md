# Local Setup Instructions

## ✅ Docker Compose Updated
The `docker-compose.yml` has been updated to include ChromaDB service.

## .env Configuration

Update your `/Users/mayursuhasiya/Desktop/Projects/ai-youtuber-studio/backend/.env` file based on how you're running the services:

### If running backend/worker LOCALLY (outside Docker):

```bash
# Local Redis (runs in Docker, accessed from host)
REDIS_URL=redis://localhost:6379/0

# Local ChromaDB (runs in Docker, accessed from host)
CHROMA_HOST=localhost
CHROMA_PORT=8001
```

### If running everything IN DOCKER:

No .env changes needed! The docker-compose.yml defaults will work:
- REDIS_URL defaults to `redis://redis:6379/0`
- CHROMA_HOST defaults to `chromadb`
- CHROMA_PORT defaults to `8000` (internal Docker port)

## Commands to Run

### Start Services in Docker

```bash
cd ~/Desktop/Projects/ai-youtuber-studio/backend
docker-compose up -d
```

This starts:
- ✅ Redis (localhost:6379) - container name: `redis`
- ✅ ChromaDB (localhost:8001) - container name: `chromadb`
- ✅ Celery Worker - container name: `worker`

### Run Backend Locally (Recommended for Development)

```bash
# Terminal 1: Start Docker services (Redis, ChromaDB, Worker)
cd ~/Desktop/Projects/ai-youtuber-studio/backend
docker-compose up -d

# Terminal 2: Start Backend locally
cd ~/Desktop/Projects/ai-youtuber-studio/backend/scripts
./start_backend.sh
```

### Alternative: Run Backend and Worker Locally

If you prefer running the worker locally too:

```bash
# Start only Redis & ChromaDB in Docker
cd ~/Desktop/Projects/ai-youtuber-studio/backend
docker-compose up -d redis chromadb

# Then run backend and worker locally (in separate terminals)
cd ~/Desktop/Projects/ai-youtuber-studio/backend/scripts
./start_backend.sh  # Terminal 1
./start_worker.sh   # Terminal 2
```

## Verification Commands

```bash
# Check all services are running
cd ~/Desktop/Projects/ai-youtuber-studio/backend
docker-compose ps

# Test Redis
redis-cli -h localhost -p 6379 ping
# Expected output: PONG

# Test ChromaDB
curl http://localhost:8001/api/v1/heartbeat
# Expected output: {"nanosecond heartbeat": ...}

# Test Backend (if running in Docker)
curl http://localhost:8000/health
# Expected output: {"status": "ok"}

# Test Backend API Docs
open http://localhost:8000/docs
```

## Stop Services

```bash
# Stop all services
cd ~/Desktop/Projects/ai-youtuber-studio/backend
docker-compose down

# Stop and remove volumes (warning: deletes data)
docker-compose down -v
```

## View Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f redis      # Container: redis
docker-compose logs -f chromadb   # Container: chromadb
docker-compose logs -f worker     # Container: worker
```

## What Changed?

- ❌ **No more EC2 dependencies** - Everything runs on your machine
- ❌ **No SSH tunnels needed** - No need to run `start_tunnels.sh`
- ✅ **Single command startup** - `docker-compose up -d` starts everything
- ✅ **Persistent data** - Redis and ChromaDB data saved in Docker volumes
- ✅ **Local development** - Easier debugging and faster iteration

## Troubleshooting

### Port Already in Use

If you get port conflicts:

```bash
# Check what's using the port
lsof -i :6379  # Redis
lsof -i :8001  # ChromaDB
lsof -i :8000  # Backend

# Kill the process or stop existing containers
docker-compose down
```

### ChromaDB Connection Issues

If ChromaDB fails to connect, check:
1. Container is running: `docker ps | grep chromadb`
2. Logs: `docker-compose logs chromadb`
3. Port is accessible: `curl http://localhost:8001/api/v1/heartbeat`

### Redis Connection Issues

If Redis fails to connect, check:
1. Container is running: `docker ps | grep redis`
2. Test connection: `redis-cli -h localhost -p 6379 ping`
3. Logs: `docker-compose logs redis`

