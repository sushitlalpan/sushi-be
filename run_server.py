#!/usr/bin/env python3
"""
Simple script to run the FastAPI server programmatically
"""
import uvicorn
from backend.fastapi.main import app

if __name__ == "__main__":
    uvicorn.run(
        "backend.fastapi.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )