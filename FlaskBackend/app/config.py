"""Application configuration module.

This module defines configuration settings for the Flask application,
including MongoDB connection details. It reads values from environment
variables (optionally from a .env file) and provides safe defaults for
local development so the app can start even if env vars are not set.

Environment Variables:
    MONGO_URI (str, optional): MongoDB connection URI, e.g., mongodb://localhost:27017
    DB_NAME (str, optional): Name of the MongoDB database (default: "devices_db").
    COLLECTION_NAME (str, optional): Name of the collection to store devices (default: "devices").
    AUDIT_COLLECTION_NAME (str, optional): Name of the collection to store audit logs (default: "audit_logs").

Notes:
    - Do not hardcode secrets. Use a .env file for local development.
    - Production deployments should override defaults via environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

# Load .env if present (no-op if not available)
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # If python-dotenv is not installed or .env is missing, ignore silently.
    pass


@dataclass(frozen=True)
class Config:
    """Immutable configuration holder for the Flask app and MongoDB settings."""

    mongo_uri: Optional[str]
    db_name: str
    collection_name: str
    audit_collection_name: str


# PUBLIC_INTERFACE
def load_config() -> Config:
    """Load configuration from environment variables with safe defaults.

    Returns:
        Config: The application configuration object.

    Behavior:
        - If MONGO_URI is not provided, the application will still start,
          but any database operations will fail at the point of DB usage.
          This enables CI/preview environments to boot without a database.
    """
    mongo_uri = os.getenv("MONGO_URI") or None
    db_name = os.getenv("DB_NAME", "devices_db")
    collection_name = os.getenv("COLLECTION_NAME", "devices")
    audit_collection_name = os.getenv("AUDIT_COLLECTION_NAME", "audit_logs")

    return Config(
        mongo_uri=mongo_uri,
        db_name=db_name,
        collection_name=collection_name,
        audit_collection_name=audit_collection_name,
    )
