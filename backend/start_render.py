#!/usr/bin/env python3
"""
Render startup script for AnemiaLens.
Uses the PORT environment variable provided by Render.
"""

import os
import uvicorn
from app.main import app

if __name__ == "__main__":
    # Render provides PORT env var, fallback to 8000 for local dev
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"Starting AnemiaLens on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
