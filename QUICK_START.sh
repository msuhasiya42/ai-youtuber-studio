#!/bin/bash

# ====================================
# AI YouTuber Studio - Analytics Engine
# Quick Start Deployment Script
# ====================================

set -e  # Exit on error

echo ""
echo "🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀"
echo "         AI YouTuber Studio - Analytics Engine Deployment"
echo "🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="/Users/mayursuhasiya/Desktop/Projects/ai-youtuber-studio"
cd "$PROJECT_ROOT"

# Step 1: Check Docker
echo "📦 Step 1: Checking Docker..."
if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running!${NC}"
    echo "Please start Docker Desktop and run this script again."
    exit 1
fi
echo -e "${GREEN}✅ Docker is running${NC}"
echo ""

# Step 2: Check .env file
echo "🔧 Step 2: Checking environment variables..."
cd backend
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit backend/.env with your credentials before continuing!${NC}"
    echo ""
    echo "Required variables:"
    echo "  - DATABASE_URL"
    echo "  - GOOGLE_CLIENT_ID"
    echo "  - GOOGLE_CLIENT_SECRET"
    echo "  - OPENAI_API_KEY (or GEMINI_API_KEY)"
    echo ""
    read -p "Press Enter after you've updated .env file..."
fi
echo -e "${GREEN}✅ .env file exists${NC}"
echo ""

# Step 3: Build Docker images
echo "🏗️  Step 3: Building Docker images..."
echo "This may take 5-10 minutes on first run..."
docker compose build
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker build failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker images built successfully${NC}"
echo ""

# Step 4: Start containers
echo "▶️  Step 4: Starting containers..."
docker compose up -d
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to start containers!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Containers started${NC}"
echo ""

# Wait for backend to be ready
echo "⏳ Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is ready${NC}"
        break
    fi
    echo -n "."
    sleep 2
done
echo ""

# Step 5: Run database migration (CRITICAL!)
echo "🗄️  Step 5: Running database migration..."
docker compose exec backend alembic upgrade head
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Migration failed!${NC}"
    echo "Check logs: docker compose logs backend"
    exit 1
fi
echo -e "${GREEN}✅ Database migration completed${NC}"
echo ""

# Step 6: Test backend
echo "🧪 Step 6: Testing backend API..."
HEALTH_CHECK=$(curl -s http://localhost:8000/api/health)
if [[ $HEALTH_CHECK == *"ok"* ]]; then
    echo -e "${GREEN}✅ Backend API is responding${NC}"
else
    echo -e "${RED}❌ Backend API health check failed${NC}"
    exit 1
fi
echo ""

# Step 7: Run test suite
echo "🧪 Step 7: Running test suite..."
docker compose exec backend python scripts/test_analytics_api.py
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Some tests failed. Check output above.${NC}"
else
    echo -e "${GREEN}✅ All tests passed${NC}"
fi
echo ""

# Step 8: Frontend setup
echo "🎨 Step 8: Setting up frontend..."
cd ../frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi

# Check if recharts is installed
if ! npm list recharts > /dev/null 2>&1; then
    echo "Installing recharts..."
    npm install recharts@^3.3.0
fi

echo -e "${GREEN}✅ Frontend dependencies ready${NC}"
echo ""

# Step 9: Display summary
echo "=" * 80
echo "🎉 DEPLOYMENT COMPLETE!"
echo "=" * 80
echo ""
echo "📊 Services Status:"
echo "-------------------"
cd ../backend
docker compose ps
echo ""
echo "🌐 URLs:"
echo "--------"
echo "Backend API:       http://localhost:8000"
echo "API Docs:          http://localhost:8000/docs"
echo "Health Check:      http://localhost:8000/api/health"
echo ""
echo "📝 Next Steps:"
echo "--------------"
echo "1. Start frontend development server:"
echo "   cd $PROJECT_ROOT/frontend"
echo "   npm run dev"
echo ""
echo "2. Open browser to:"
echo "   http://localhost:5173/analytics"
echo ""
echo "3. Log in with YouTube account"
echo ""
echo "4. Click 'Sync Analytics' button"
echo ""
echo "5. Explore analytics, patterns, and AI insights!"
echo ""
echo "📚 Documentation:"
echo "-----------------"
echo "Deployment Guide:  $PROJECT_ROOT/ANALYTICS_DEPLOYMENT_GUIDE.md"
echo "Implementation:    $PROJECT_ROOT/IMPLEMENTATION_COMPLETE.md"
echo ""
echo "🛠️  Useful Commands:"
echo "--------------------"
echo "View logs:         cd backend && docker compose logs -f"
echo "Stop services:     cd backend && docker compose down"
echo "Restart:           cd backend && docker compose restart"
echo ""
echo "✅ All systems ready! Happy analyzing! 🚀"
echo ""

