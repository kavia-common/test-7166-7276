"""Flask application factory and API setup.

This module creates the Flask app, configures extensions, wires routes using
Flask-RESTful, and integrates the device repository backed by MongoDB.
"""

from __future__ import annotations

from flask import Flask
from flask_cors import CORS
from flask_restful import Api

from .config import load_config
from .db import create_repository
from .resources import DevicesResource, DeviceResource, PingResource
from .audit import init_audit
from pymongo import MongoClient


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
    repo = create_repository(cfg.mongo_uri, cfg.db_name, cfg.collection_name)

    # Initialize audit logging collection
    client = MongoClient(cfg.mongo_uri)
    audit_collection = client[cfg.db_name][cfg.audit_collection_name]
    init_audit(audit_collection)

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
        return {"message": "Healthy"}, 200

    return app
