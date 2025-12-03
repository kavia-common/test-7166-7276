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
        if err:
            return err

        created, db_err = self.repo.create_device(payload)  # type: ignore[arg-type]
        if db_err:
            if "already exists" in db_err:
                return _error(HTTPStatus.CONFLICT, db_err)
            return _error(HTTPStatus.INTERNAL_SERVER_ERROR, db_err)

        return created, HTTPStatus.CREATED


class DeviceResource(Resource):
    """Resource for retrieving, updating, and deleting a single device."""

    def __init__(self, repo: DeviceRepository) -> None:
        """Initialize with repository."""
        self.repo = repo

    # PUBLIC_INTERFACE
    def get(self, name: str):
        """Get a single device by name."""
        device = self.repo.get_device(name)
        if not device:
            return _error(HTTPStatus.NOT_FOUND, "Device not found.")
        return device, HTTPStatus.OK

    # PUBLIC_INTERFACE
    def put(self, name: str):
        """Update fields of a device by name."""
        data = request.get_json(silent=True) or {}
        payload, err = _validate_update_payload(data)
        if err:
            return err
        updated, db_err = self.repo.update_device(name, payload)  # type: ignore[arg-type]
        if db_err:
            if "not found" in db_err.lower():
                return _error(HTTPStatus.NOT_FOUND, db_err)
            return _error(HTTPStatus.INTERNAL_SERVER_ERROR, db_err)
        return updated, HTTPStatus.OK

    # PUBLIC_INTERFACE
    def delete(self, name: str):
        """Delete a device by name."""
        deleted, db_err = self.repo.delete_device(name)
        if db_err:
            if "not found" in db_err.lower():
                return _error(HTTPStatus.NOT_FOUND, db_err)
            return _error(HTTPStatus.INTERNAL_SERVER_ERROR, db_err)
        if not deleted:
            return _error(HTTPStatus.NOT_FOUND, "Device not found.")
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
        device = self.repo.get_device(name)
        if not device:
            return _error(HTTPStatus.NOT_FOUND, "Device not found.")
        ip = device["ip"]
        try:
            # Send a couple of pings with a short timeout for responsiveness
            result = ping(ip, count=2, timeout=1)
            reachable = result.success()
            rtt_ms = float(result.rtt_avg_ms) if hasattr(result, "rtt_avg_ms") else 0.0
            payload = {
                "reachable": bool(reachable),
                "rtt_ms": rtt_ms,
                "error": None if reachable else "Timeout or unreachable",
            }
            return payload, HTTPStatus.OK
        except Exception as exc:  # broad except to catch system-level ping errors
            return {
                "reachable": False,
                "rtt_ms": 0.0,
                "error": f"Ping failed: {exc}",
            }, HTTPStatus.OK
