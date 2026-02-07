"""
BiasFree News - FastAPI Application
Main entry point for the backend server with automated scraping.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.config import settings
from app.database.database import init_db
from app.services.scheduler import get_scheduler

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Reduce noise from third-party libraries
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('apscheduler').setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.debug("=" * 80)
    logger.debug(f"Starting BiasFree News API - Environment: {settings.environment}")
    logger.debug(f"Using OpenAI model: {settings.openai_model}")
    logger.debug(f"Rate limit: {settings.rate_limit_per_minute} requests/minute")
    
    # Initialize database
    logger.debug("Initializing database...")
    init_db()
    logger.debug("Database initialized successfully")
    
    # Create admin user if not exists
    logger.debug("Creating admin user if not exists...")
    from app.database.database import SessionLocal
    from app.services.auth_service import AuthService
    db = SessionLocal()
    try:
        admin = AuthService.create_admin_user(db)
        if admin:
            logger.info(f"Admin user created: {admin.username} ({admin.email})")
        else:
            logger.debug("Admin user already exists")
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
    finally:
        db.close()
    
    # Start scheduler for automated scraping
    logger.debug("Starting automated scraping scheduler...")
    scheduler = get_scheduler()
    scheduler.start()
    logger.debug("Scheduler started - Daily scraping at 6:00 AM BDT")
    logger.debug("=" * 80)
    
    yield
    
    # Shutdown
    logger.info("Shutting down BiasFree News API")
    scheduler.stop()
    logger.info("Scheduler stopped")


# Initialize FastAPI application
app = FastAPI(
    title="BiasFree News API",
    description="API for detecting and removing bias from Bengali news articles",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
from app.api.routes_enhanced import limiter, router
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Include main API routes
app.include_router(router)

# Include manual processing routes (NEW - for on-demand bias analysis)
from app.api.manual_processing import router as manual_router
app.include_router(manual_router)

# Include authentication routes
from app.api.auth_routes import router as auth_router
app.include_router(auth_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.debug else "An error occurred"
        }
    )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "BiasFree News API",
        "version": "1.0.0",
        "description": "Detect and remove bias from Bengali news articles",
        "docs": "/docs" if settings.debug else "disabled",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )