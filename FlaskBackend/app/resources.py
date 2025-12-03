"""Flask-RESTful resources for the Device Management API.

This module defines the REST endpoints for managing devices and pinging them.
It uses a DeviceRepository for persistence and pythonping for health checks.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, List, Tuple, TypedDict

from flask import request
from flask_restful import Resource
from pythonping import ping

from .db import DeviceRepository
from .audit import log_audit


class DevicePayload(TypedDict):
    """TypedDict for device payload used in create operations."""
    name: str
    ip: str
    type: str
    location: str


class DeviceUpdatePayload(TypedDict):
    """TypedDict for device update payload."""
    ip: str
    type: str
    location: str


ALLOWED_TYPES = {"Router", "Switch", "Server"}


def _validate_ipv4(ip: str) -> bool:
    """Simple IPv4 validation."""
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


def _error(code: int, message: str, details: Dict[str, Any] | None = None) -> Tuple[Dict[str, Any], int]:
    """Format an error response and HTTP status code."""
    return {"code": str(code), "message": message, "details": details or {}}, code


def _validate_create_payload(data: Dict[str, Any]) -> Tuple[Dict[str, Any] | None, Tuple[Dict[str, Any], int] | None]:
    """Validate create device payload."""
    missing = [f for f in ("name", "ip", "type", "location") if f not in data or data[f] in (None, "")]
    if missing:
        return None, _error(HTTPStatus.BAD_REQUEST, "Missing required fields.", {"missing": missing})

    if not _validate_ipv4(str(data["ip"])):
        return None, _error(HTTPStatus.BAD_REQUEST, "Invalid IPv4 address.", {"field": "ip"})

    if data["type"] not in ALLOWED_TYPES:
        return None, _error(HTTPStatus.BAD_REQUEST, "Invalid device type.", {"allowed": sorted(ALLOWED_TYPES)})

    payload: DevicePayload = {
        "name": str(data["name"]),
        "ip": str(data["ip"]),
        "type": str(data["type"]),
        "location": str(data["location"]),
    }
    return payload, None


def _validate_update_payload(data: Dict[str, Any]) -> Tuple[Dict[str, Any] | None, Tuple[Dict[str, Any], int] | None]:
    """Validate update device payload."""
    missing = [f for f in ("ip", "type", "location") if f not in data or data[f] in (None, "")]
    if missing:
        return None, _error(HTTPStatus.BAD_REQUEST, "Missing required fields.", {"missing": missing})

    if not _validate_ipv4(str(data["ip"])):
        return None, _error(HTTPStatus.BAD_REQUEST, "Invalid IPv4 address.", {"field": "ip"})

    if data["type"] not in ALLOWED_TYPES:
        return None, _error(HTTPStatus.BAD_REQUEST, "Invalid device type.", {"allowed": sorted(ALLOWED_TYPES)})

    payload: DeviceUpdatePayload = {
        "ip": str(data["ip"]),
        "type": str(data["type"]),
        "location": str(data["location"]),
    }
    return payload, None


class DevicesResource(Resource):
    """Resource for listing and creating devices."""

    def __init__(self, repo: DeviceRepository) -> None:
        """Initialize the resource with a repository."""
        self.repo = repo

    # PUBLIC_INTERFACE
    def get(self):
        """List all devices.

        Returns:
            tuple[list[dict], int]: The list of devices and HTTP 200.
        """
        devices: List[Dict[str, Any]] = self.repo.list_devices()
        # Audit: viewing list (no specific device)
        ip = request.remote_addr
        log_audit(action="view", device_name=None, status="success", details={"endpoint": "GET /devices"}, ip=ip)
        return devices, HTTPStatus.OK

    # PUBLIC_INTERFACE
    def post(self):
        """Create a new device.

        Expected JSON body:
            {
                "name": "router-1",
                "ip": "192.168.1.1",
                "type": "Router",
                "location": "DC1"
            }

        Returns:
            tuple[dict, int]: The created device and HTTP 201, or an error.
        """
        data = request.get_json(silent=True) or {}
        payload, err = _validate_create_payload(data)
        ip = request.remote_addr
        if err:
            # Audit failure
            log_audit(action="create", device_name=data.get("name") if isinstance(data, dict) else None,
                      status="failure", details={"error": err[0]["message"], "endpoint": "POST /devices"}, ip=ip)
            return err

        created, db_err = self.repo.create_device(payload)  # type: ignore[arg-type]
        if db_err:
            status_code = HTTPStatus.CONFLICT if "already exists" in db_err else HTTPStatus.INTERNAL_SERVER_ERROR
            log_audit(action="create", device_name=payload["name"], status="failure",
                      details={"error": db_err, "status_code": int(status_code), "endpoint": "POST /devices"}, ip=ip)
            if "already exists" in db_err:
                return _error(HTTPStatus.CONFLICT, db_err)
            return _error(HTTPStatus.INTERNAL_SERVER_ERROR, db_err)

        log_audit(action="create", device_name=payload["name"], status="success",
                  details={"endpoint": "POST /devices"}, ip=ip)
        return created, HTTPStatus.CREATED


class DeviceResource(Resource):
    """Resource for retrieving, updating, and deleting a single device."""

    def __init__(self, repo: DeviceRepository) -> None:
        """Initialize with repository."""
        self.repo = repo

    # PUBLIC_INTERFACE
    def get(self, name: str):
        """Get a single device by name."""
        ip = request.remote_addr
        device = self.repo.get_device(name)
        if not device:
            log_audit(action="view", device_name=name, status="failure",
                      details={"error": "Device not found.", "endpoint": "GET /devices/{name}"}, ip=ip)
            return _error(HTTPStatus.NOT_FOUND, "Device not found.")
        log_audit(action="view", device_name=name, status="success",
                  details={"endpoint": "GET /devices/{name}"}, ip=ip)
        return device, HTTPStatus.OK

    # PUBLIC_INTERFACE
    def put(self, name: str):
        """Update fields of a device by name."""
        data = request.get_json(silent=True) or {}
        payload, err = _validate_update_payload(data)
        ip = request.remote_addr
        if err:
            log_audit(action="edit", device_name=name, status="failure",
                      details={"error": err[0]["message"], "endpoint": "PUT /devices/{name}"}, ip=ip)
            return err
        updated, db_err = self.repo.update_device(name, payload)  # type: ignore[arg-type]
        if db_err:
            status = HTTPStatus.NOT_FOUND if "not found" in db_err.lower() else HTTPStatus.INTERNAL_SERVER_ERROR
            log_audit(action="edit", device_name=name, status="failure",
                      details={"error": db_err, "status_code": int(status), "endpoint": "PUT /devices/{name}"}, ip=ip)
            if "not found" in db_err.lower():
                return _error(HTTPStatus.NOT_FOUND, db_err)
            return _error(HTTPStatus.INTERNAL_SERVER_ERROR, db_err)
        log_audit(action="edit", device_name=name, status="success",
                  details={"endpoint": "PUT /devices/{name}"}, ip=ip)
        return updated, HTTPStatus.OK

    # PUBLIC_INTERFACE
    def delete(self, name: str):
        """Delete a device by name."""
        ip = request.remote_addr
        deleted, db_err = self.repo.delete_device(name)
        if db_err:
            status = HTTPStatus.NOT_FOUND if "not found" in db_err.lower() else HTTPStatus.INTERNAL_SERVER_ERROR
            log_audit(action="delete", device_name=name, status="failure",
                      details={"error": db_err, "status_code": int(status), "endpoint": "DELETE /devices/{name}"}, ip=ip)
            if "not found" in db_err.lower():
                return _error(HTTPStatus.NOT_FOUND, db_err)
            return _error(HTTPStatus.INTERNAL_SERVER_ERROR, db_err)
        if not deleted:
            log_audit(action="delete", device_name=name, status="failure",
                      details={"error": "Device not found.", "endpoint": "DELETE /devices/{name}"}, ip=ip)
            return _error(HTTPStatus.NOT_FOUND, "Device not found.")
        log_audit(action="delete", device_name=name, status="success",
                  details={"endpoint": "DELETE /devices/{name}"}, ip=ip)
        return "", HTTPStatus.NO_CONTENT


class PingResource(Resource):
    """Resource for pinging a device by name."""

    def __init__(self, repo: DeviceRepository) -> None:
        """Initialize with repository."""
        self.repo = repo

    # PUBLIC_INTERFACE
    def get(self, name: str):
        """Ping the device IP associated with given name.

        Returns:
            tuple[dict, int]: Ping result and HTTP 200, or error/404.
        """
        requester_ip = request.remote_addr
        device = self.repo.get_device(name)
        if not device:
            log_audit(action="ping", device_name=name, status="failure",
                      details={"error": "Device not found.", "endpoint": "GET /ping/{name}"}, ip=requester_ip)
            return _error(HTTPStatus.NOT_FOUND, "Device not found.")
        target_ip = device["ip"]
        try:
            # Send a couple of pings with a short timeout for responsiveness
            result = ping(target_ip, count=2, timeout=1)
            reachable = result.success()
            rtt_ms = float(result.rtt_avg_ms) if hasattr(result, "rtt_avg_ms") else 0.0
            payload = {
                "reachable": bool(reachable),
                "rtt_ms": rtt_ms,
                "error": None if reachable else "Timeout or unreachable",
            }
            log_audit(action="ping", device_name=name,
                      status="success" if reachable else "failure",
                      details={"endpoint": "GET /ping/{name}", "target_ip": target_ip, "reachable": bool(reachable),
                               "rtt_ms": rtt_ms}, ip=requester_ip)
            return payload, HTTPStatus.OK
        except Exception as exc:  # broad except to catch system-level ping errors
            log_audit(action="ping", device_name=name, status="failure",
                      details={"error": f"Ping failed: {exc}", "endpoint": "GET /ping/{name}", "target_ip": target_ip},
                      ip=requester_ip)
            return {
                "reachable": False,
                "rtt_ms": 0.0,
                "error": f"Ping failed: {exc}",
            }, HTTPStatus.OK
