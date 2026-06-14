"""
Script to run the FastAPI server.
"""

import sys
import os

# Avoid unnecessary HuggingFace network checks during local demos.
# The embedding model must already be available in the local cache.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load .env file BEFORE importing settings (PHASE 8)
# Simple loading - if file has issues, it will be skipped
try:
    load_dotenv(encoding='utf-8')
except:
    # If encoding fails, just skip .env file (use defaults)
    pass

import uvicorn
from app.config import settings


def main():
    """Run the FastAPI application."""
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Environment: {settings.environment}")
    print(f"Host: {settings.api_host}:{settings.api_port}")
    print(f"Debug: {settings.debug}")
    print(f"Web UI: http://127.0.0.1:{settings.api_port}/")
    print(f"API docs: http://127.0.0.1:{settings.api_port}/docs")
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()

