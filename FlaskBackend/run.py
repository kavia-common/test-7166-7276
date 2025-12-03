"""Development entry point for the Flask application.

Run with:
    python run.py

Environment:
    FLASK_HOST (optional): Host to bind (default 0.0.0.0)
    FLASK_PORT (optional): Port to bind (default 5000)
"""

from __future__ import annotations

import os

from app import app

if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5000"))
    app.run(host=host, port=port)
