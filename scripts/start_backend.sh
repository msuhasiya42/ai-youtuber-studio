#!/bin/bash

# Backend Startup Script for AI YouTuber Studio
# Starts the FastAPI backend server with proper configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}AI YouTuber Studio - Backend Startup${NC}"
echo "========================================"
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

# Check if virtual environment exists
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating one...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Install/upgrade dependencies
echo ""
echo "Checking dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Run database migrations
echo ""
echo "Running database migrations..."
alembic upgrade head || {
    echo -e "${YELLOW}Warning: Migration failed. If this is first run, initialize DB with:${NC}"
    echo "  python init_db.py"
}

# Load environment variables
echo ""
echo "Loading environment variables from .env..."
set -a
source .env
set +a

# Check critical environment variables
MISSING_VARS=()

[ -z "$DATABASE_URL" ] && MISSING_VARS+=("DATABASE_URL")
[ -z "$REDIS_URL" ] && MISSING_VARS+=("REDIS_URL")
[ -z "$CHROMA_HOST" ] && MISSING_VARS+=("CHROMA_HOST")
[ -z "$AWS_S3_BUCKET" ] && MISSING_VARS+=("AWS_S3_BUCKET")
[ -z "$AWS_ACCESS_KEY_ID" ] && MISSING_VARS+=("AWS_ACCESS_KEY_ID")
[ -z "$AWS_SECRET_ACCESS_KEY" ] && MISSING_VARS+=("AWS_SECRET_ACCESS_KEY")
[ -z "$GEMINI_API_KEY" ] && MISSING_VARS+=("GEMINI_API_KEY")

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}Error: Missing required environment variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please update your .env file"
    exit 1
fi

echo -e "${GREEN}✓ All required environment variables set${NC}"

# Start the backend server
echo ""
echo -e "${GREEN}Starting FastAPI backend server...${NC}"
echo ""
echo "Server will be available at: http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
