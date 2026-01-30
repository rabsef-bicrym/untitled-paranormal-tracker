#!/bin/bash
# Start the paranormal tracker web application

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Paranormal Tracker Web Application${NC}"
echo ""

# Check if database is running
echo -e "${YELLOW}Checking database...${NC}"
if ! PGPASSWORD=paranormal psql -h localhost -p 5433 -U paranormal -d paranormal_tracker -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}Database not running. Starting with docker-compose...${NC}"
    cd "$PROJECT_ROOT"
    docker-compose up -d
    echo "Waiting for database to be ready..."
    sleep 5
fi

# Start backend
echo -e "${YELLOW}Starting FastAPI backend on port 8000...${NC}"
cd "$SCRIPT_DIR/backend"

# Check for venv
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# Set environment variables if not set
export DATABASE_URL="${DATABASE_URL:-postgresql://paranormal:paranormal@localhost:5433/paranormal_tracker}"

# Start backend in background
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend started with PID $BACKEND_PID"

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}Backend is ready!${NC}"
        break
    fi
    sleep 1
done

# Start frontend
echo -e "${YELLOW}Starting SvelteKit frontend on port 5173...${NC}"
cd "$SCRIPT_DIR/frontend"
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!
echo "Frontend started with PID $FRONTEND_PID"

echo ""
echo -e "${GREEN}Application started!${NC}"
echo -e "  Backend:  http://localhost:8000"
echo -e "  Frontend: http://localhost:5173"
echo -e "  API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"

# Trap to clean up background processes
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}Done${NC}"
}
trap cleanup EXIT

# Wait for either process to exit
wait
