"""
FastAPI application entry point.
Serves the IT support assistant API endpoints.
"""

from dotenv import load_dotenv

# Load .env file BEFORE importing settings (PHASE 8: Critical for OpenAI API key)
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import structlog
from pathlib import Path

from app.config import settings
from app.routers import chat, health, anomaly

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Context-aware IT support assistant with hybrid RAG and anomaly detection",
    debug=settings.debug
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
# Health endpoint at both root and versioned API path for convenience
app.include_router(health.router, tags=["health"])  # Root level: /health
app.include_router(health.router, prefix="/api/v1", tags=["health"])  # Versioned: /api/v1/health
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(anomaly.router, prefix="/api/v1", tags=["anomaly"])

# ============================================
# PHASE 6: Static Files for Web UI
# ============================================
# Mount frontend directory to serve HTML/CSS/JS
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/ui", StaticFiles(directory=str(frontend_path)), name="frontend")
    logger.info("frontend_mounted", path=str(frontend_path))
    
    # Root path redirects to Web UI
    @app.get("/", include_in_schema=False)
    async def root():
        """Serve the Web UI at root path."""
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Frontend not found. Please check frontend/ directory."}
else:
    logger.warning("frontend_directory_not_found", path=str(frontend_path))


@app.on_event("startup")
async def startup_event():
    """Initialize resources on application startup."""
    logger.info("application_startup", environment=settings.environment)
    # TODO: Initialize models, indexes, etc.


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on application shutdown."""
    logger.info("application_shutdown")
    # TODO: Cleanup resources


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )


