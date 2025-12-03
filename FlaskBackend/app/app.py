"""Flask application factory and API setup.

This module creates the Flask app, configures extensions, wires routes using
Flask-RESTful, and integrates the device repository backed by MongoDB.
"""

from __future__ import annotations

from flask import Flask
from flask_cors import CORS
from flask_restful import Api

from .config import load_config
from .db import create_repository, DeviceRepository
from .resources import DevicesResource, DeviceResource, PingResource
from .audit import init_audit
from pymongo import MongoClient


class InMemoryDeviceRepository(DeviceRepository):
    """A minimal in-memory repository used when MongoDB is not configured.

    This repository supports the same public methods as DeviceRepository
    so the application can run in preview/CI environments without MongoDB.
    """

    def __init__(self) -> None:
        # type: ignore[call-arg] (super expects a Collection; we bypass it)
        self._items: dict[str, dict] = {}

    def list_devices(self):
        return list(self._items.values())

    def get_device(self, name: str):
        return dict(self._items.get(name)) if name in self._items else None

    def create_device(self, device):
        name = device.get("name")
        if not name:
            return None, "Missing device name."
        if name in self._items:
            return None, "A device with this name already exists."
        self._items[name] = dict(device)
        return dict(self._items[name]), None

    def update_device(self, name: str, updates):
        if name not in self._items:
            return None, "Device not found."
        self._items[name].update(dict(updates))
        return dict(self._items[name]), None

    def delete_device(self, name: str):
        if name not in self._items:
            return False, "Device not found."
        del self._items[name]
        return True, None


# PUBLIC_INTERFACE
def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        Flask: The configured Flask application.
    """
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Load configuration and repository
    cfg = load_config()

    # When no MONGO_URI is set, switch to in-memory repo and skip audit DB init.
    if not cfg.mongo_uri:
        repo = InMemoryDeviceRepository()
        audit_initialized = False
    else:
        repo = create_repository(cfg.mongo_uri, cfg.db_name, cfg.collection_name)
        # Initialize audit logging collection
        try:
            client = MongoClient(cfg.mongo_uri)
            audit_collection = client[cfg.db_name][cfg.audit_collection_name]
            init_audit(audit_collection)
            audit_initialized = True
        except Exception:
            # If audit init fails, continue without blocking startup
            audit_initialized = False

    # Set up Flask-RESTful
    api = Api(app, prefix="")
    api.add_resource(
        DevicesResource,
        "/devices",
        resource_class_kwargs={"repo": repo},
        endpoint="devices",
    )
    api.add_resource(
        DeviceResource,
        "/devices/<string:name>",
        resource_class_kwargs={"repo": repo},
        endpoint="device",
    )
    api.add_resource(
        PingResource,
        "/ping/<string:name>",
        resource_class_kwargs={"repo": repo},
        endpoint="ping",
    )

    # Basic health route
    @app.get("/")
    def health():
        """Health check endpoint.

        Returns:
            dict: Service status payload.
        """
        return {"message": "Healthy", "audit": "on" if audit_initialized else "off"}, 200

    return app
