"""
PrepPilot FastAPI application.

Main application entry point with route registration, CORS, and background jobs.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.config import settings
from backend.api.routes import auth, plans, fridge, recipes, export, email, admin, features
from backend.middleware.csrf import CSRFMiddleware
from backend.jobs.freshness_decay import start_scheduler, stop_scheduler
from backend.db.database import SessionLocal
from sqlalchemy import text

# Configure logging with configurable level
_log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
logging.basicConfig(
    level=_log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiter for auth endpoints (shared across routes)
# Disabled in debug mode for easier testing
limiter = Limiter(key_func=get_remote_address, enabled=not settings.debug)

# Global scheduler instance
scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    global scheduler
    scheduler = start_scheduler()

    yield

    # Shutdown
    logger.info("Shutting down application...")
    if scheduler:
        stop_scheduler(scheduler)


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Adaptive meal planning and prep optimization API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add rate limiter to app state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add CSRF protection middleware
# Note: Middleware executes in reverse order of addition, so CSRF runs after CORS
app.add_middleware(
    CSRFMiddleware,
    allowed_origins=settings.cors_origins,
    enabled=not settings.debug,  # Disabled in debug mode for easier testing
    exempt_paths=["/health", "/docs", "/redoc", "/openapi.json"],
)

# Register routers
app.include_router(auth.router)
app.include_router(plans.router)
app.include_router(fridge.router)
app.include_router(recipes.router)
app.include_router(export.router)
app.include_router(email.router)
app.include_router(admin.router)
app.include_router(features.router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with database connectivity test."""
    db_status = "healthy"
    db_error = None

    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e)

    overall_status = "healthy" if db_status == "healthy" else "unhealthy"

    response = {
        "status": overall_status,
        "version": settings.app_version,
        "database": db_status,
    }

    if db_error:
        response["database_error"] = db_error

    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
