"""
Script to run the FastAPI server.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load .env file BEFORE importing settings (PHASE 8)
load_dotenv()

import uvicorn
from app.config import settings


def main():
    """Run the FastAPI application."""
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Environment: {settings.environment}")
    print(f"Host: {settings.api_host}:{settings.api_port}")
    print(f"Debug: {settings.debug}")
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()

