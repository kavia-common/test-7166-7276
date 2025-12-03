"""Audit logging module for tracking API actions.

This module provides a simple helper function to log audit events to a MongoDB
collection using pymongo. It is designed to be initialized once during app
startup and then used throughout request handling to record user actions.

Log schema:
    {
        "action": str,           # e.g., "create", "edit", "view", "delete", "ping"
        "device_name": str|null, # target device if applicable
        "ip": str|null,          # request remote IP
        "timestamp": datetime,   # UTC timestamp of event
        "status": str,           # "success" | "failure"
        "details": dict|null     # optional additional info
    }
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pymongo.collection import Collection


@dataclass
class AuditContext:
    """Holds the initialized audit collection reference for logging."""
    collection: Collection


# Module-level holder for initialized audit collection
_audit_ctx: Optional[AuditContext] = None


# PUBLIC_INTERFACE
def init_audit(collection: Collection) -> None:
    """Initialize the audit logger with a MongoDB collection.

    Args:
        collection (Collection): The MongoDB collection where audit logs are stored.
    """
    global _audit_ctx
    _audit_ctx = AuditContext(collection=collection)
    # Optional: index to query by time or action if needed in the future
    try:
        collection.create_index("timestamp")
        collection.create_index("action")
        collection.create_index("device_name")
        collection.create_index("status")
    except Exception:
        # Index creation should not break the app if it fails; ignore quietly.
        pass


# PUBLIC_INTERFACE
def log_audit(action: str, device_name: Optional[str], status: str, details: Optional[Dict[str, Any]] = None,
              ip: Optional[str] = None) -> None:
    """Log an audit record into MongoDB.

    This function is safe to call even if the audit module has not been
    initialized; in that case it will no-op.

    Args:
        action (str): The action performed (create, edit, view, delete, ping).
        device_name (str | None): The device name if applicable.
        status (str): Outcome status ("success" or "failure").
        details (dict | None): Optional detail payload.
        ip (str | None): Request IP address if available.

    Returns:
        None
    """
    if _audit_ctx is None:
        # Not initialized; do nothing.
        return
    doc: Dict[str, Any] = {
        "action": str(action),
        "device_name": device_name if device_name is not None else None,
        "ip": ip if ip else None,
        "timestamp": datetime.now(timezone.utc),
        "status": str(status),
        "details": details or None,
    }
    # Best-effort logging; avoid raising to callers.
    try:
        _audit_ctx.collection.insert_one(doc)
    except Exception:
        # Swallow errors to avoid breaking API flow due to logging failures.
        pass
