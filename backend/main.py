"""FastAPI entrypoint.

Run from the backend/ directory:
    uvicorn main:app --reload --port 8000
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.routes import app  # noqa: E402,F401  (re-exported for uvicorn main:app)
