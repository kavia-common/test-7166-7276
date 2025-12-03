# Flask Backend - Device Management API

RESTful API for managing network devices and performing health checks (ping).
Implements CRUD operations for devices stored in MongoDB via `pymongo` and
ping using `pythonping`. Configuration is provided via environment variables
with sensible local defaults to allow preview/CI to start even without MongoDB.

## Requirements

- Python 3.10+
- Optional: A reachable MongoDB instance (local or remote) if you want persistence
- Optional: `.env` file to configure environment variables

## Setup

1. (Optional) Create a `.env` file based on `.env.example` to point to your MongoDB.
2. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

3. Run the server:

```bash
python run.py
```

By default, the server runs on `http://0.0.0.0:5000`.

## Configuration and Defaults

The app loads environment variables from `.env` if present and supports overrides
from the host environment. If required variables are not provided, the app will
still start using an in-memory repository (no persistence) so that previews work.

- `MONGO_URI` (optional): MongoDB connection string. If omitted, the app uses an in-memory repository.
- `DB_NAME` (optional): Database name (default `devices_db`).
- `COLLECTION_NAME` (optional): Collection where devices are stored (default `devices`).
- `AUDIT_COLLECTION_NAME` (optional): Collection for audit logs (default `audit_logs`).
- `FLASK_HOST` (optional): Host to bind (default `0.0.0.0`).
- `FLASK_PORT` (optional): Port to bind (default `5000`).

If `MONGO_URI` is provided, the app connects to MongoDB using `DB_NAME` and
`COLLECTION_NAME`. If audit initialization fails, the app continues to run without it.

## API Endpoints

- `GET /devices` - List all devices
- `POST /devices` - Create a device (name unique)
- `GET /devices/{name}` - Get a device by name
- `PUT /devices/{name}` - Update device fields (ip, type, location)
- `DELETE /devices/{name}` - Delete a device
- `GET /ping/{name}` - Ping device by name (returns reachable and rtt_ms)

## Error Handling

- 400 Bad Request: Invalid input or missing fields.
- 404 Not Found: Device not found.
- 409 Conflict: Duplicate device name.
- 500 Internal Server Error: Unexpected server/database errors.

## Notes

- All modules, classes, and functions have docstrings and follow PEP 8.
- MongoDB unique index on `name` is enforced at runtime by the repository.
- Audit logs are written to MongoDB using `AUDIT_COLLECTION_NAME` (default `audit_logs`) when MongoDB is configured.
- When running without MongoDB (no `MONGO_URI`), data is stored in memory for the process lifetime only.
