# Flask Backend - Device Management API

RESTful API for managing network devices and performing health checks (ping).
Implements CRUD operations for devices stored in MongoDB via `pymongo` and
ping using `pythonping`. Configuration is provided via environment variables.

## Requirements

- Python 3.10+
- A reachable MongoDB instance (local or remote)
- Environment variables set (see `.env.example`)

## Setup

1. Create and populate a `.env` file based on `.env.example`.
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

## Environment Variables

- `MONGO_URI` (required): MongoDB connection string.
- `DB_NAME` (required): Database name.
- `COLLECTION_NAME` (required): Collection name where devices are stored.
- `FLASK_HOST` (optional): Host to bind (default `0.0.0.0`).
- `FLASK_PORT` (optional): Port to bind (default `5000`).

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
