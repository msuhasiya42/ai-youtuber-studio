#!/bin/bash

# SSH Tunnel Manager for AI YouTuber Studio
# This script creates SSH tunnels to EC2 for Redis and ChromaDB

set -e

# Configuration
EC2_IP="34.229.175.124"
PEM_KEY="$HOME/Desktop/AWS/ai-youtuber-studio-key.pem"
PID_FILE="$HOME/.ai-youtuber-studio-tunnels.pid"
LOG_FILE="$HOME/.ai-youtuber-studio-tunnels.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}AI YouTuber Studio - SSH Tunnel Manager${NC}"
echo "============================================"
echo ""

# Check if PEM key exists
if [ ! -f "$PEM_KEY" ]; then
    echo -e "${RED}Error: PEM key not found at $PEM_KEY${NC}"
    echo "Please update the PEM_KEY variable in this script"
    exit 1
fi

# Check if tunnels are already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}SSH tunnels are already running (PID: $OLD_PID)${NC}"
        echo "To restart, first run: kill $OLD_PID"
        exit 0
    else
        echo -e "${YELLOW}Removing stale PID file${NC}"
        rm "$PID_FILE"
    fi
fi

# Start SSH tunnel
echo "Starting SSH tunnels to EC2..."
echo "  → Redis: localhost:6379 → EC2:6379"
echo "  → ChromaDB: localhost:8001 → EC2:8001"
echo ""

nohup ssh -i "$PEM_KEY" \
    -N \
    -L 6379:127.0.0.1:6379 \
    -L 8001:127.0.0.1:8001 \
    -o ServerAliveInterval=60 \
    -o ServerAliveCountMax=3 \
    -o ExitOnForwardFailure=yes \
    ubuntu@"$EC2_IP" \
    > "$LOG_FILE" 2>&1 &

TUNNEL_PID=$!

# Save PID
echo "$TUNNEL_PID" > "$PID_FILE"

# Wait a moment for tunnel to establish
sleep 2

# Check if tunnel is still running
if ps -p "$TUNNEL_PID" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ SSH tunnels started successfully (PID: $TUNNEL_PID)${NC}"
    echo ""
    echo "Tunnels are running in the background."
    echo ""
    echo "To check status:"
    echo "  ps -p $TUNNEL_PID"
    echo ""
    echo "To view logs:"
    echo "  tail -f $LOG_FILE"
    echo ""
    echo "To stop tunnels:"
    echo "  kill $TUNNEL_PID"
    echo "  rm $PID_FILE"
    echo ""
else
    echo -e "${RED}✗ Failed to start SSH tunnels${NC}"
    echo "Check logs: cat $LOG_FILE"
    rm "$PID_FILE"
    exit 1
fi
