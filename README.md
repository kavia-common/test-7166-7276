# test-7166-7276

This project includes a Flask backend for device management and a React frontend (not shown here).
The Flask backend now starts even if MongoDB environment variables are not set by using an
in-memory repository for preview/CI environments. To enable persistence, set MONGO_URI (and
optionally DB_NAME, COLLECTION_NAME) in a `.env` file within `FlaskBackend/` or export them
in your environment. See `FlaskBackend/.env.example` for details.