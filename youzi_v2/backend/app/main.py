"""
Unified ASGI entry (optional).

Development: run legacy API and Vite separately (see README).
Production: build frontend then `uvicorn youzi_v2.backend.app.main:app`.
"""

from youzi_v2.app import app  # noqa: F401
