"""Vercel entrypoint.

Vercel's Python runtime loads a top-level ``app`` from a supported filename
(``server.py`` is one). The real application lives in
``frontend/api/server.py``; this shim only puts the project root on the path
and re-exports it, so the same code runs locally and on Vercel.

Local run:  uvicorn frontend.api.server:app --port 8601
Vercel run: this module (server.py) is the function entrypoint.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.api.server import app  # noqa: E402,F401

__all__ = ["app"]
