#!/usr/bin/env python3
"""
NEPTUNE Backend — Development Server Launcher
Run: python run.py
"""
import uvicorn
from app.config.settings import get_settings

settings = get_settings()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.backend_reload,
        log_level=settings.log_level.lower(),
        workers=1,  # Always 1 in development with reload=True
    )
