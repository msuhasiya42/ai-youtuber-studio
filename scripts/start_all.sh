#!/bin/bash

# Master Startup Script for AI YouTuber Studio
# Starts all services in the correct order

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

clear
echo -e "${MAGENTA}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║        AI YouTuber Studio - Complete Startup              ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -i :"$1" >/dev/null 2>&1
}

# Prerequisites check
echo -e "${BLUE}Step 1: Checking prerequisites...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

MISSING=()

command_exists python3 || MISSING+=("python3")
command_exists pip || MISSING+=("pip")
command_exists redis-cli || MISSING+=("redis-cli (optional for testing)")
command_exists ssh || MISSING+=("ssh")

if [ ${#MISSING[@]} -gt 0 ]; then
    echo -e "${RED}✗ Missing required tools:${NC}"
    for tool in "${MISSING[@]}"; do
        echo "  - $tool"
    done
    exit 1
fi

echo -e "${GREEN}✓ All required tools are installed${NC}"
echo ""

# Step 2: Start SSH tunnels
echo -e "${BLUE}Step 2: Starting SSH tunnels (Redis & ChromaDB)...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

"$SCRIPT_DIR/start_tunnels.sh"
echo ""

# Wait for tunnels to be ready
echo "Waiting for tunnels to establish..."
sleep 3

# Test tunnel connections
echo "Testing tunnel connections..."

if port_in_use 6379; then
    echo -e "${GREEN}✓ Redis tunnel (port 6379) is active${NC}"
else
    echo -e "${YELLOW}⚠ Redis tunnel may not be ready${NC}"
fi

if port_in_use 8001; then
    echo -e "${GREEN}✓ ChromaDB tunnel (port 8001) is active${NC}"
else
    echo -e "${YELLOW}⚠ ChromaDB tunnel may not be ready${NC}"
fi

echo ""

# Step 3: Test connections
echo -e "${BLUE}Step 3: Testing service connections...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$SCRIPT_DIR/../backend"

# Source .env
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Test Redis
if redis-cli -u "$REDIS_URL" ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis connection successful${NC}"
else
    echo -e "${RED}✗ Redis connection failed${NC}"
    echo "  Make sure SSH tunnel is running"
fi

# Test ChromaDB
if curl -s "http://$CHROMA_HOST:$CHROMA_PORT/api/v1/heartbeat" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ ChromaDB connection successful${NC}"
else
    echo -e "${YELLOW}⚠ ChromaDB connection failed${NC}"
    echo "  Make sure SSH tunnel is running and ChromaDB is up on EC2"
fi

echo ""

# Step 4: Start services in separate terminal windows
echo -e "${BLUE}Step 4: Starting application services...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${YELLOW}Starting services in new terminal windows...${NC}"
echo ""

# Detect OS and open terminals accordingly
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - use osascript to open new Terminal tabs

    # Start Backend
    osascript <<EOF
tell application "Terminal"
    do script "cd '$SCRIPT_DIR' && ./start_backend.sh"
    activate
end tell
EOF

    sleep 2

    # Start Worker
    osascript <<EOF
tell application "Terminal"
    do script "cd '$SCRIPT_DIR' && ./start_worker.sh"
end tell
EOF

    echo -e "${GREEN}✓ Opened Backend and Worker in new Terminal windows${NC}"

elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux - try gnome-terminal or xterm
    if command_exists gnome-terminal; then
        gnome-terminal -- bash -c "cd '$SCRIPT_DIR' && ./start_backend.sh; exec bash"
        gnome-terminal -- bash -c "cd '$SCRIPT_DIR' && ./start_worker.sh; exec bash"
    elif command_exists xterm; then
        xterm -e "cd '$SCRIPT_DIR' && ./start_backend.sh" &
        xterm -e "cd '$SCRIPT_DIR' && ./start_worker.sh" &
    else
        echo -e "${YELLOW}Please run these commands in separate terminals:${NC}"
        echo "  Terminal 1: ./scripts/start_backend.sh"
        echo "  Terminal 2: ./scripts/start_worker.sh"
    fi
else
    echo -e "${YELLOW}Please run these commands in separate terminals:${NC}"
    echo "  Terminal 1: ./scripts/start_backend.sh"
    echo "  Terminal 2: ./scripts/start_worker.sh"
fi

echo ""
echo -e "${MAGENTA}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║                                                           ║${NC}"
echo -e "${MAGENTA}║                   Startup Complete! 🚀                    ║${NC}"
echo -e "${MAGENTA}║                                                           ║${NC}"
echo -e "${MAGENTA}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Your AI YouTuber Studio is starting up!${NC}"
echo ""
echo "Services:"
echo "  ✓ SSH Tunnels (Redis + ChromaDB)"
echo "  ✓ Backend API (http://localhost:8000)"
echo "  ✓ Celery Worker (background tasks)"
echo ""
echo "Next steps:"
echo "  1. Wait ~10 seconds for backend to start"
echo "  2. Check API docs: http://localhost:8000/docs"
echo "  3. Start frontend: cd frontend && npm run dev"
echo ""
echo "To stop all services:"
echo "  1. Press Ctrl+C in Backend and Worker terminals"
echo "  2. Run: kill \$(cat ~/.ai-youtuber-studio-tunnels.pid)"
echo ""
