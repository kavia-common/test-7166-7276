"""Health blueprint (flask-smorest) for documentation compatibility.

Note:
    The main app uses Flask-RESTful and defines a health route directly.
    This blueprint remains for compatibility and potential doc generation.
"""

from __future__ import annotations

from flask.views import MethodView
from flask_smorest import Blueprint

blp = Blueprint(
    "Health Check",
    "health-check",
    url_prefix="/",
    description="Health check route",
)


@blp.route("/")
class HealthCheck(MethodView):
    """Health check view."""

    # PUBLIC_INTERFACE
    def get(self):
        """Return a simple health payload."""
        return {"message": "Healthy"}
