#!/bin/bash
# Clear Celery queue to remove old tasks

echo "🧹 Clearing Celery queue..."

# Connect to Redis and flush the Celery queues
docker compose exec redis redis-cli -n 0 FLUSHDB

echo "✅ Celery queue cleared!"
echo ""
echo "Next steps:"
echo "1. Restart the Celery worker: docker compose restart celery-worker"
echo "2. Re-sync your channel videos from the UI or API"
echo "3. Videos will be queued properly with the race condition fix"

