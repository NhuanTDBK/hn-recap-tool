"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.presentation.api import auth, digests
from app.infrastructure.config.settings import settings
from app.infrastructure.services.redis_cache import RedisCacheService
from app.infrastructure.jobs.data_collector import DataCollectorJob
from app.presentation.api.dependencies import (
    get_collect_posts_use_case,
    get_extract_content_use_case,
    get_create_digest_use_case
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
cache_service: RedisCacheService = None
collector_job: DataCollectorJob = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Initialize Redis cache
    global cache_service
    cache_service = RedisCacheService()
    logger.info("Redis cache service initialized")

    # Initialize and start data collector job
    global collector_job
    collector_job = DataCollectorJob(
        collect_posts_use_case=get_collect_posts_use_case(),
        extract_content_use_case=get_extract_content_use_case(),
        create_digest_use_case=get_create_digest_use_case()
    )
    collector_job.start()
    logger.info("Data collector job started")

    yield

    # Shutdown
    logger.info("Shutting down application")

    # Stop data collector job
    if collector_job:
        collector_job.stop()
        logger.info("Data collector job stopped")

    # Close Redis connection
    if cache_service:
        await cache_service.close()
        logger.info("Redis cache connection closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="HackerNews digest backend API with clean architecture",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(digests.router)


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "redis": "connected" if cache_service else "disconnected",
        "collector": "running" if collector_job else "stopped"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
