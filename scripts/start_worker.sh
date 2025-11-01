#!/bin/bash

# Celery Worker Startup Script for AI YouTuber Studio
# Starts the Celery worker for background task processing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}AI YouTuber Studio - Celery Worker Startup${NC}"
echo "=============================================="
echo ""

# Navigate to backend directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

cd "$BACKEND_DIR"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found in $BACKEND_DIR${NC}"
    echo "Please create a .env file with required configuration"
    exit 1
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo -e "${RED}Error: Virtual environment not found${NC}"
    echo "Please run start_backend.sh first to create the virtual environment"
    exit 1
fi

echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Load environment variables
echo ""
echo "Loading environment variables from .env..."
set -a
source .env
set +a

# Check Redis connection
if [ -n "$REDIS_URL" ]; then
    echo ""
    echo "Checking Redis connection..."
    if redis-cli -u "$REDIS_URL" ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis is reachable${NC}"
    else
        echo -e "${YELLOW}Warning: Cannot connect to Redis${NC}"
        echo "Make sure SSH tunnels are running:"
        echo "  ./scripts/start_tunnels.sh"
    fi
fi

# Start Celery worker
echo ""
echo -e "${GREEN}Starting Celery worker...${NC}"
echo ""
echo "Worker queues:"
echo "  - ingest (audio download)"
echo "  - transcribe (Whisper API)"
echo "  - embedding (vector embeddings)"
echo "  - generation (RAG script generation)"
echo "  - insights (performance analysis)"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the worker${NC}"
echo ""

# Start worker with all queues
celery -A celery_worker.app worker \
    --loglevel=INFO \
    --concurrency=4 \
    --queues=ingest,transcribe,embedding,generation,insights
