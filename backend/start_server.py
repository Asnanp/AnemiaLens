#!/usr/bin/env python3
"""
Generic startup script for hosted AnemiaLens backends.
Uses PORT and HOST environment variables when provided by the host.
"""

import os

import uvicorn

from app.main import app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    print(f"Starting AnemiaLens on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
