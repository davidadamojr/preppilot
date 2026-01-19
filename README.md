# PrepPilot - Adaptive Meal Prep Autopilot

An adaptive meal planning platform for restrictive diets (starting with low-histamine). PrepPilot intelligently adjusts meal plans when you skip prep days or delay cooking.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [Running the Application](#running-the-application)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [CLI Usage](#cli-usage)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Background Jobs](#background-jobs)
- [Troubleshooting](#troubleshooting)
- [Future Enhancements](#future-enhancements)

## Features

- **Diet-Aware Meal Plans**: Generates 3-day meal plans tailored to dietary restrictions (low-histamine, FODMAP, fructose-free)
- **Dietary Exclusions**: Supports 18+ allergen/exclusion categories (peanuts, tree nuts, dairy, gluten, nightshades, etc.)
- **Freshness Tracking**: Monitors ingredient freshness with daily decay and expiration alerts
- **Adaptive Replanning**: Automatically adjusts meal plans when preps are missed
- **Prep Optimization**: Batches similar cooking steps to minimize prep time
- **Fridge Inventory**: Tracks what's in your fridge with expiration management
- **PDF Export**: Generate printable meal plans with prep instructions
- **Email Notifications**: Send meal plans directly to your inbox
- **JWT Authentication**: Secure user accounts with rate-limited auth endpoints

## Tech Stack

### Backend
- **Framework**: FastAPI with Uvicorn
- **Database**: PostgreSQL 15+ with SQLAlchemy ORM
- **Migrations**: Alembic
- **Authentication**: JWT with bcrypt password hashing
- **Background Jobs**: APScheduler
- **PDF Generation**: ReportLab

### Frontend
- **Framework**: Next.js 14 with React 18
- **Styling**: Tailwind CSS with shadcn/ui components
- **State Management**: TanStack React Query
- **HTTP Client**: Axios
- **Icons**: Lucide React

## Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 15+ (or Docker)
- pip and npm

## Quick Start

### Backend Setup

```bash
# Clone the repository
git clone <repository-url>
cd preppilot

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env - IMPORTANT: Set a secure SECRET_KEY (see below)
```

> **Security Note**: The application requires a secure `SECRET_KEY` when running with `DEBUG=false` (default). Generate one with `openssl rand -hex 32` and set it in your `.env` file. The app will refuse to start in production mode with the default insecure key.

#### Database Setup

**Option 1: Docker (Recommended)**

```bash
docker compose up -d
```

This starts PostgreSQL on port 5432 with:
- Database: `preppilot`
- User: `preppilot`
- Password: `preppilot`

**Option 2: Manual PostgreSQL**

```bash
# Create database and user
createdb preppilot
createuser preppilot
psql -d preppilot -c "ALTER USER preppilot WITH PASSWORD 'preppilot';"
psql -d preppilot -c "GRANT ALL PRIVILEGES ON DATABASE preppilot TO preppilot;"
```

#### Initialize Database

```bash
# Run migrations
PYTHONPATH=. python3 -m alembic -c backend/alembic.ini upgrade head

# Seed recipe database
python3 -m backend.db.seed
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local if your API runs on a different URL
```

## Running the Application

### Quick Start (Recommended)

Use the development script to start both frontend and backend with a single command:

```bash
# Start both servers (uses Docker for PostgreSQL)
./scripts/dev.sh

# Start with native PostgreSQL instead of Docker
./scripts/dev.sh --no-docker

# Reset database, reseed, and start
./scripts/dev.sh --reset

# Reset with native PostgreSQL
./scripts/dev.sh --reset --no-docker
```

The script will:
- Check and install dependencies if needed
- Ensure PostgreSQL is running
- Start both backend and frontend concurrently
- Handle graceful shutdown with Ctrl+C

### Manual Start

#### Start the Backend API

```bash
# From project root, with virtual environment activated
python3 -m backend.main
```

Or using uvicorn directly:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

#### Start the Frontend

```bash
cd frontend
npm run dev
```

The frontend will be available at http://localhost:3000

### Verify Setup

After starting the servers, verify everything is working:

```bash
# Check backend health (should return status: healthy)
curl http://localhost:8000/health

# Check API docs load
open http://localhost:8000/docs  # or visit in browser

# Check frontend loads
open http://localhost:3000  # or visit in browser
```

### Database Reset

To clear the database and reseed:

```bash
# Using the dev script (recommended)
./scripts/dev.sh --reset

# Or manually:
# With Docker:
docker exec preppilot_db psql -U preppilot -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" preppilot

# With native PostgreSQL:
psql postgresql://preppilot:preppilot@localhost:5432/preppilot -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Then run migrations and seed:
PYTHONPATH=. python3 -m alembic -c backend/alembic.ini upgrade head
python3 -m backend.db.seed
```

## Configuration

### Backend Environment Variables (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://preppilot:preppilot@localhost:5432/preppilot` |
| `SECRET_KEY` | JWT signing key (change in production!) | - |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration | `10080` (7 days) |
| `CORS_ORIGINS` | Allowed frontend origins | `http://localhost:3000,http://localhost:8000` |
| `DEBUG` | Enable debug mode | `false` |
| `ENABLE_BACKGROUND_JOBS` | Enable scheduled tasks | `true` |
| `FRESHNESS_DECAY_HOUR` | Hour to run daily freshness decay (0-23) | `0` |
| `EMAIL_ENABLED` | Enable email features | `false` |
| `SMTP_SERVER` | SMTP server address | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_USERNAME` | SMTP username | - |
| `SMTP_PASSWORD` | SMTP password | - |

Generate a secure secret key:
```bash
openssl rand -hex 32
```

### Frontend Environment Variables (.env.local)

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000` |

## API Documentation

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | Create new user account |
| `/auth/login` | POST | Get JWT token |
| `/auth/me` | GET | Get current user info |

### Meal Plans

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/plans` | POST | Generate new meal plan |
| `/api/plans` | GET | List user's meal plans |
| `/api/plans/{id}` | GET | Get specific plan |
| `/api/plans/{id}/mark-prep` | PATCH | Mark meal as done/skipped |
| `/api/plans/{id}/adapt` | POST | Trigger adaptive replanning |
| `/api/plans/{id}/catch-up` | GET | Get catch-up suggestions |
| `/api/plans/{id}` | DELETE | Delete plan |

### Fridge Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/fridge` | GET | Get current fridge state |
| `/api/fridge/items` | POST | Add single item |
| `/api/fridge/items/bulk` | POST | Add multiple items |
| `/api/fridge/items/{id}` | DELETE | Remove item by ID |
| `/api/fridge/items/by-name/{name}` | DELETE | Remove by ingredient name |
| `/api/fridge/expiring` | GET | Get items expiring soon |
| `/api/fridge` | DELETE | Clear all items |

### Recipes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/recipes` | GET | List recipes (with filters) |
| `/api/recipes/{id}` | GET | Get recipe details |
| `/api/recipes/search/by-ingredient` | GET | Search by ingredient |

### Additional

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/export` | POST | Generate PDF meal plan |
| `/api/email` | POST | Email meal plan |
| `/health` | GET | Health check (includes DB connectivity) |

### Rate Limiting

Authentication endpoints are rate-limited to prevent abuse:
- `/auth/register`: 10 requests per minute
- `/auth/login`: 5 requests per minute

Rate limiting is disabled when `DEBUG=true` for easier development.

### Example API Usage

```bash
# Register a new user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secure123","diet_type":"low_histamine"}'

# Login and get token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secure123"}'

# Generate meal plan (use token from login)
curl -X POST http://localhost:8000/api/plans \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"start_date":"2025-12-06","days":3}'

# Add items to fridge
curl -X POST http://localhost:8000/api/fridge/items/bulk \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"items":[{"ingredient_name":"chicken","quantity":"500g","freshness_days":3}]}'

# Mark meal as done
curl -X PATCH http://localhost:8000/api/plans/{PLAN_ID}/mark-prep \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"date":"2025-12-06","meal_type":"breakfast","status":"done"}'
```

## CLI Usage

The backend includes a CLI for testing and demonstration:

```bash
# Generate a new 3-day meal plan
python -m backend.cli generate

# Stock fridge with ingredients from plan
python -m backend.cli stock

# View current fridge state
python -m backend.cli fridge

# Mark a meal prep as done or skipped
python -m backend.cli mark-prep 2025-12-06 breakfast done
python -m backend.cli mark-prep 2025-12-06 lunch skipped

# Trigger adaptive replanning
python -m backend.cli adapt

# Show optimized prep timeline for a date
python -m backend.cli optimize 2025-12-06
```

## Testing

### Backend Tests

```bash
# Run all tests
pytest backend/tests/ -v

# Run with coverage report
pytest backend/tests/ --cov=backend --cov-report=html

# Run specific test file
pytest backend/tests/test_auth_routes.py -v
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm run test

# Run with UI
npm run test:ui

# Run with coverage
npm run test:coverage
```

## Project Structure

```
preppilot/
├── backend/
│   ├── api/
│   │   ├── routes/           # API endpoints (auth, plans, fridge, recipes)
│   │   └── dependencies.py   # Auth dependencies
│   ├── auth/                 # JWT and password utilities
│   ├── db/
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── database.py       # Session management
│   │   └── seed.py           # Recipe seeding
│   ├── engine/               # Core adaptive logic
│   │   ├── meal_generator.py
│   │   ├── freshness_tracker.py
│   │   ├── adaptive_planner.py
│   │   └── prep_optimizer.py
│   ├── services/             # Business logic layer
│   ├── jobs/                 # Background jobs
│   ├── models/               # Pydantic schemas
│   ├── alembic/              # Database migrations
│   ├── tests/                # Test suite
│   ├── config.py             # Application config
│   ├── cli.py                # CLI interface
│   └── main.py               # FastAPI app entry point
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js App Router pages
│   │   │   ├── login/
│   │   │   ├── register/
│   │   │   └── dashboard/
│   │   ├── components/
│   │   │   ├── ui/           # shadcn/ui components
│   │   │   └── dashboard/    # Dashboard components
│   │   ├── lib/              # Utilities and API client
│   │   ├── hooks/            # Custom React hooks
│   │   └── types/            # TypeScript types
│   ├── package.json
│   └── tailwind.config.ts
├── docs/
│   ├── prompts/              # Development prompts
│   ├── auth_migration.md     # Auth migration guide
│   └── GUIDELINES.md         # Development guidelines
├── scripts/
│   └── dev.sh                # Development server script
├── docker-compose.yml        # PostgreSQL container
├── .env.example              # Backend env template
└── README.md
```

## Background Jobs

The API includes scheduled background jobs:

| Job | Schedule | Description |
|-----|----------|-------------|
| Freshness Decay | Daily (configurable hour) | Decrements fridge item freshness by 1 day |
| Cleanup | Weekly (Sunday 2 AM) | Removes expired items |

Disable with `ENABLE_BACKGROUND_JOBS=false` in `.env`.

## Troubleshooting

### Common Issues

**Backend fails to start with "SECURITY ERROR"**
```
SECURITY ERROR: You must set a secure SECRET_KEY environment variable
```
You need to generate and set a secure secret key in your `.env` file:
```bash
openssl rand -hex 32
```
Copy the output and set it as `SECRET_KEY` in `.env`.

**Database connection failed**
- Ensure PostgreSQL is running: `docker ps` (for Docker) or `pg_isready` (native)
- Check that `DATABASE_URL` in `.env` matches your database configuration
- For Docker: Run `docker compose up -d` to start the container

**Migrations fail**
- Make sure the database exists and is accessible
- Run from project root with `PYTHONPATH=.`:
  ```bash
  PYTHONPATH=. python3 -m alembic -c backend/alembic.ini upgrade head
  ```

**Port 8000 or 3000 already in use**
- Find and kill the process: `lsof -i :8000` then `kill <PID>`
- Or use a different port: `uvicorn backend.main:app --port 8001`

**Frontend can't connect to backend**
- Check that `NEXT_PUBLIC_API_URL` in `frontend/.env.local` is correct
- Ensure the backend is running and accessible
- Check CORS settings in backend `.env`

## Future Enhancements

- Calendar sync integration (Google Calendar, Apple Calendar)
- Push notifications for prep reminders
- Shopping list generation
- Recipe suggestions based on fridge contents
- Multi-user household support

See [docs/prompts/00_master_prompt.md](docs/prompts/00_master_prompt.md) for the full roadmap.

## License

MIT
