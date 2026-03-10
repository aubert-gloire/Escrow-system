"""
FastAPI Backend Application
Runs on Render for webhook endpoints and API access
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from contextlib import asynccontextmanager
from database.mongo import MongoDB
from config.settings import settings
from loguru import logger
import uvicorn


# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    logger.info("🚀 Backend starting...")
    await MongoDB.connect_db()
    yield
    # Shutdown
    logger.info("🛑 Backend shutting down...")
    await MongoDB.close_db()


# Create FastAPI app
app = FastAPI(
    title="Escrow Bot Phase 1 API",
    description="Backend API for Escrow Bot",
    version="1.0.0",
    lifespan=lifespan
)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "escrow-bot-backend"
    }


# API dependency
async def get_db() -> AsyncIOMotorDatabase:
    """Get database."""
    return MongoDB.get_db()


# Import routes
from backend.routes import deals, admin


# Include routers
app.include_router(deals.router, prefix="/api/deals", tags=["Deals"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower()
    )
