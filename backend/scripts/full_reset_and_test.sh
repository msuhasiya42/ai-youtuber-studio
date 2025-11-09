#!/bin/bash
# Complete reset and test script for caption processing

echo "🔄 Full Reset and Test Process"
echo "================================"
echo ""

echo "Step 1: Stopping Celery worker..."
docker compose stop celery-worker
echo "✅ Worker stopped"
echo ""

echo "Step 2: Clearing Redis Celery queues..."
docker compose exec redis redis-cli -n 0 FLUSHDB
echo "✅ Queue cleared"
echo ""

echo "Step 3: Restarting Celery worker with new code..."
docker compose up -d celery-worker
sleep 3
echo "✅ Worker restarted"
echo ""

echo "Step 4: Checking worker status..."
docker compose logs celery-worker --tail=20
echo ""

echo "================================"
echo "✅ System reset complete!"
echo ""
echo "Next steps:"
echo "1. Go to your UI and re-sync a channel"
echo "2. Choose a popular channel (most have captions enabled)"
echo "3. Watch the logs: docker compose logs -f celery-worker"
echo ""
echo "Good channels to test with (have captions):"
echo "  - Fireship (@fireship_dev)"
echo "  - ThePrimeagen (@ThePrimeagen)"
echo "  - Web Dev Simplified (@WebDevSimplified)"
echo ""
echo "Expected results:"
echo "  ✅ Videos with captions: Successfully processed"
echo "  ⚠️  Videos without captions: Clear error message"
echo "  ✅ No 'Video X not found in database' errors"
echo "  ✅ No AttributeError crashes"

