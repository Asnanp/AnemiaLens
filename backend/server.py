"""
Bridge module for supervisor — exposes `app` at module level.
Supervisor runs: uvicorn server:app --host 0.0.0.0 --port 8001
"""
from app.main import app  # noqa: F401
