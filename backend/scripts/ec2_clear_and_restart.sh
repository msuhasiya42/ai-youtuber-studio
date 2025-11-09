#!/bin/bash
# Script to run on EC2 to clear Redis queue and restart worker
# This removes old tasks that reference non-existent videos

echo "🧹 Clearing Redis Celery Queue on EC2"
echo "========================================"
echo ""

# Navigate to project directory
cd /home/ubuntu/ai-youtuber-studio/backend || exit 1

echo "Step 1: Clearing Redis database (removing old tasks)..."
sudo docker exec ai-youtuber-redis redis-cli -n 0 FLUSHDB
if [ $? -eq 0 ]; then
    echo "✅ Redis queue cleared"
else
    echo "❌ Failed to clear Redis"
    exit 1
fi
echo ""

echo "Step 2: Restarting worker container..."
sudo docker restart ai-youtuber-worker
sleep 5
echo "✅ Worker restarted"
echo ""

echo "Step 3: Checking container status..."
sudo docker compose -f docker-compose.prod.yml ps
echo ""

echo "Step 4: Checking worker health..."
if sudo docker exec ai-youtuber-worker celery -A celery_worker inspect ping; then
    echo "✅ Worker is healthy"
else
    echo "⚠️  Worker may still be starting up..."
fi
echo ""

echo "Step 5: Tailing worker logs (press Ctrl+C to exit)..."
echo "Watch for: No more 'Video X not found in database' errors"
echo "-----------------------------------------------------------"
sleep 2
sudo docker logs -f ai-youtuber-worker

