"""
Health check endpoints for monitoring and readiness probes.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
import structlog

from app.config import settings

router = APIRouter()
logger = structlog.get_logger()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str
    environment: str


class ReadinessResponse(BaseModel):
    """Readiness check response with component status."""
    status: str
    components: Dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.
    Returns 200 if the service is running.
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment
    )


@router.get("/readiness", response_model=ReadinessResponse)
async def readiness_check() -> ReadinessResponse:
    """
    Readiness check endpoint.
    Verifies that all required components (models, indexes, etc.) are loaded.
    """
    components = {
        "api": "ready",
        # TODO: Check actual component status
        "llm": "not_loaded",
        "embeddings": "not_loaded",
        "bm25_index": "not_loaded",
        "vector_index": "not_loaded",
    }
    
    all_ready = all(status == "ready" for status in components.values())
    
    return ReadinessResponse(
        status="ready" if all_ready else "not_ready",
        components=components
    )


