#!/usr/bin/env python3
"""
Run the Vietnam Stock Trader backend server
"""
import uvicorn
import sys
import os

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings

if __name__ == "__main__":
    print("=" * 50)
    print("Vietnam Stock Trader - Backend Server")
    print("=" * 50)
    print(f"Starting server at http://{settings.api_host}:{settings.api_port}")
    print(f"API Documentation: http://localhost:{settings.api_port}/docs")
    print(f"Auto-trading: {'Enabled' if settings.enable_auto_trading else 'Disabled'}")
    print("=" * 50)

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info"
    )
