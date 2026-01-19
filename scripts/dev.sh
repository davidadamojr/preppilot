#!/bin/bash
set -e

# PrepPilot Development Script
# Usage: ./scripts/dev.sh [options]
#
# Options:
#   --reset      Clear database and reseed before starting
#   --no-docker  Use native PostgreSQL instead of Docker
#   --help       Show this help message

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
RESET_DB=false
USE_DOCKER=true

for arg in "$@"; do
    case $arg in
        --reset)
            RESET_DB=true
            shift
            ;;
        --no-docker)
            USE_DOCKER=false
            shift
            ;;
        --help)
            echo "PrepPilot Development Script"
            echo ""
            echo "Usage: ./scripts/dev.sh [options]"
            echo ""
            echo "Options:"
            echo "  --reset      Clear database and reseed before starting"
            echo "  --no-docker  Use native PostgreSQL instead of Docker"
            echo "  --help       Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./scripts/dev.sh                    # Start with Docker PostgreSQL"
            echo "  ./scripts/dev.sh --no-docker        # Start with native PostgreSQL"
            echo "  ./scripts/dev.sh --reset            # Reset DB and start (Docker)"
            echo "  ./scripts/dev.sh --reset --no-docker # Reset DB and start (native)"
            exit 0
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  PrepPilot Development Server${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if we're in the project root
cd "$PROJECT_ROOT"

# Check for required tools
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}Error: $1 is not installed${NC}"
        exit 1
    fi
}

check_command python3
check_command npm

# Check for psql if using native PostgreSQL
if [ "$USE_DOCKER" = false ]; then
    check_command psql
else
    check_command docker
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}Installing backend dependencies...${NC}"
    pip install -r backend/requirements.txt
fi

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    cd frontend && npm install && cd ..
fi

# Database setup
if [ "$USE_DOCKER" = true ]; then
    echo -e "${BLUE}Checking PostgreSQL container...${NC}"
    if ! docker ps | grep -q preppilot_db; then
        echo -e "${YELLOW}Starting PostgreSQL container...${NC}"
        docker compose up -d
        echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
        sleep 3
    fi

    # Wait for PostgreSQL to be ready
    until docker exec preppilot_db pg_isready -U preppilot > /dev/null 2>&1; do
        echo -e "${YELLOW}Waiting for PostgreSQL...${NC}"
        sleep 1
    done
    echo -e "${GREEN}PostgreSQL container is ready${NC}"
else
    echo -e "${BLUE}Using native PostgreSQL...${NC}"
    # Check if PostgreSQL is running
    if ! pg_isready > /dev/null 2>&1; then
        echo -e "${RED}Error: PostgreSQL is not running${NC}"
        echo -e "${YELLOW}Start PostgreSQL with: sudo systemctl start postgresql${NC}"
        exit 1
    fi
    echo -e "${GREEN}PostgreSQL is ready${NC}"
fi

# Reset database if requested
if [ "$RESET_DB" = true ]; then
    echo ""
    echo -e "${YELLOW}Resetting database...${NC}"

    # Use Alembic to cleanly downgrade all migrations, then upgrade
    # This avoids needing schema ownership (DROP SCHEMA requires superuser)
    echo -e "${BLUE}Downgrading all migrations...${NC}"
    PYTHONPATH=. python3 -m alembic -c backend/alembic.ini downgrade base 2>/dev/null || true

    # Drop any remaining enum types that might not be cleaned up
    if [ "$USE_DOCKER" = true ]; then
        docker exec preppilot_db psql -U preppilot -c "DROP TYPE IF EXISTS diettype CASCADE; DROP TYPE IF EXISTS prepstatus CASCADE; DROP TYPE IF EXISTS auditaction CASCADE; DROP TYPE IF EXISTS userrole CASCADE;" preppilot 2>/dev/null || true
    else
        source .env 2>/dev/null || true
        psql "${DATABASE_URL:-postgresql://preppilot:preppilot@localhost:5432/preppilot}" -c "DROP TYPE IF EXISTS diettype CASCADE; DROP TYPE IF EXISTS prepstatus CASCADE; DROP TYPE IF EXISTS auditaction CASCADE; DROP TYPE IF EXISTS userrole CASCADE;" 2>/dev/null || true
    fi

    echo -e "${GREEN}Database cleared${NC}"

    # Run migrations
    echo -e "${BLUE}Running migrations...${NC}"
    PYTHONPATH=. python3 -m alembic -c backend/alembic.ini upgrade head
    echo -e "${GREEN}Migrations complete${NC}"

    # Seed database
    echo -e "${BLUE}Seeding database...${NC}"
    python3 -m backend.db.seed
    echo -e "${GREEN}Database seeded${NC}"
fi

echo ""
echo -e "${GREEN}Starting development servers...${NC}"
echo -e "${BLUE}Backend:  ${NC}http://localhost:8000"
echo -e "${BLUE}Frontend: ${NC}http://localhost:3000"
echo -e "${BLUE}API Docs: ${NC}http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
python3 -m backend.main &
BACKEND_PID=$!

# Start frontend
cd frontend && npm run dev &
FRONTEND_PID=$!

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
