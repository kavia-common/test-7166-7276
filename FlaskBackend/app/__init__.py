"""Application package initializer.

This module exposes a ready-to-run Flask app instance using the application
factory pattern from app.app. It keeps compatibility with the existing
entry point (run.py).
"""

from __future__ import annotations

from .app import create_app

# Create the application instance for WSGI servers and run.py
app = create_app()
