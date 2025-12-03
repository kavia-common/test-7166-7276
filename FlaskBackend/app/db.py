"""Database access layer for the device management application.

This module encapsulates MongoDB access via pymongo and provides helper
functions for CRUD operations on the devices collection.

All functions return plain Python dicts suitable for JSON serialization.

Device document structure:
    {
        "name": str,          # unique identifier
        "ip": str,            # IPv4 address
        "type": str,          # one of ["Router", "Switch", "Server"]
        "location": str       # human-readable location
    }
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pymongo import MongoClient, ReturnDocument
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError


class DeviceRepository:
    """Repository for device documents backed by a MongoDB collection."""

    def __init__(self, collection: Collection) -> None:
        """Initialize the repository.

        Args:
            collection (Collection): The MongoDB collection to use.
        """
        self._col = collection
        # Ensure a unique index on the device name to prevent duplicates.
        self._col.create_index("name", unique=True)

    # PUBLIC_INTERFACE
    def list_devices(self) -> List[Dict[str, Any]]:
        """Return all devices.

        Returns:
            list[dict]: A list of all device dicts.
        """
        # Exclude MongoDB internal _id from responses
        return [self._strip_id(doc) for doc in self._col.find({}, {"_id": 0})]

    # PUBLIC_INTERFACE
    def get_device(self, name: str) -> Optional[Dict[str, Any]]:
        """Fetch a device by its unique name.

        Args:
            name (str): Device name.

        Returns:
            dict | None: The device if found, otherwise None.
        """
        return self._col.find_one({"name": name}, {"_id": 0})

    # PUBLIC_INTERFACE
    def create_device(self, device: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Create a new device.

        Args:
            device (dict): The device document to insert.

        Returns:
            tuple[dict|None, str|None]: (inserted_device, error_message)
                - inserted_device is the created device (without _id) on success
                - error_message contains reason on error (e.g., duplicate)
        """
        try:
            self._col.insert_one(device)
            # Return the inserted document without _id
            return self.get_device(device["name"]), None
        except DuplicateKeyError:
            return None, "A device with this name already exists."
        except PyMongoError as exc:
            return None, f"Database error: {exc}"

    # PUBLIC_INTERFACE
    def update_device(self, name: str, updates: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Update fields of a device by name.

        Args:
            name (str): The unique device name.
            updates (dict): Fields to update (ip, type, location).

        Returns:
            tuple[dict|None, str|None]: (updated_device, error_message)
        """
        try:
            updated = self._col.find_one_and_update(
                {"name": name},
                {"$set": updates},
                return_document=ReturnDocument.AFTER,
                projection={"_id": 0},
            )
            if not updated:
                return None, "Device not found."
            return updated, None
        except PyMongoError as exc:
            return None, f"Database error: {exc}"

    # PUBLIC_INTERFACE
    def delete_device(self, name: str) -> Tuple[bool, Optional[str]]:
        """Delete a device by name.

        Args:
            name (str): Device name.

        Returns:
            tuple[bool, str|None]: (deleted, error_message)
        """
        try:
            res = self._col.delete_one({"name": name})
            if res.deleted_count == 0:
                return False, "Device not found."
            return True, None
        except PyMongoError as exc:
            return False, f"Database error: {exc}"

    @staticmethod
    def _strip_id(doc: Dict[str, Any]) -> Dict[str, Any]:
        """Return a copy of a document without the MongoDB _id field."""
        if not doc:
            return doc
        doc = dict(doc)
        doc.pop("_id", None)
        return doc


# PUBLIC_INTERFACE
def create_repository(mongo_uri: str, db_name: str, collection_name: str) -> DeviceRepository:
    """Create a DeviceRepository connected to the specified MongoDB.

    Args:
        mongo_uri (str): MongoDB URI.
        db_name (str): Database name.
        collection_name (str): Collection name.

    Returns:
        DeviceRepository: A repository instance ready for use.
    """
    client = MongoClient(mongo_uri)
    db = client[db_name]
    collection = db[collection_name]
    return DeviceRepository(collection)
