"""Application configuration module.

This module defines configuration settings for the Flask application,
including MongoDB connection details. It reads values from environment
variables and provides a default structure for local development.

Environment Variables:
    MONGO_URI (str): MongoDB connection URI, e.g., mongodb+srv://user:pass@host/db
    DB_NAME (str): Name of the MongoDB database.
    COLLECTION_NAME (str): Name of the collection to store devices.

Notes:
    - Do not hardcode secrets. Ensure .env is used in development environments.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Immutable configuration holder for the Flask app and MongoDB settings."""

    mongo_uri: str
    db_name: str
    collection_name: str


# PUBLIC_INTERFACE
def load_config() -> Config:
    """Load configuration from environment variables.

    Returns:
        Config: The application configuration object.

    Raises:
        ValueError: If any required environment variable is missing.
    """
    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME")
    collection_name = os.getenv("COLLECTION_NAME")

    missing = [name for name, val in {
        "MONGO_URI": mongo_uri,
        "DB_NAME": db_name,
        "COLLECTION_NAME": collection_name,
    }.items() if not val]

    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    return Config(
        mongo_uri=mongo_uri,
        db_name=db_name,
        collection_name=collection_name,
    )
