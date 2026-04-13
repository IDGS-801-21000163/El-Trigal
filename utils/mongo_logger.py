import datetime
import logging
from typing import Optional

from pymongo import MongoClient


SENSITIVE_FIELDS = {
    "clave",
    "password",
    "contrasena",
    "token",
    "otp",
    "secret",
    "api_key",
    "foto",
    "imagen",
    "avatar",
    "archivo",
}


_mongo_client: Optional[MongoClient] = None


def _get_client(mongo_uri: str) -> MongoClient:
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(mongo_uri)
    return _mongo_client


def _serialize_value(value):
    if value is None:
        return None
    if isinstance(value, (int, float, str, bool)):
        return value
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    try:
        return float(value)
    except Exception:
        pass
    if isinstance(value, (bytes, bytearray)):
        return "<binary>"
    return str(value)


class MongoLogHandler(logging.Handler):
    def __init__(self, mongo_uri: str, db_name: str, collection_name: str) -> None:
        super().__init__()
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.collection_name = collection_name
        self._client: Optional[MongoClient] = None

    def _get_collection(self):
        if self._client is None:
            self._client = MongoClient(self.mongo_uri)
        return self._client[self.db_name][self.collection_name]

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload = {
                "timestamp": datetime.datetime.utcnow(),
                "level": record.levelname,
                "message": record.getMessage(),
                "logger": record.name,
                "module": record.module,
                "funcName": record.funcName,
                "line": record.lineno,
            }
            if record.exc_info:
                payload["exception"] = logging.Formatter().formatException(record.exc_info)
            self._get_collection().insert_one(payload)
        except Exception:
            self.handleError(record)


def configure_mongo_logging(app):
    mongo_uri = app.config.get("MONGO_URI")
    db_name = app.config.get("MONGO_DB", "panaderia")
    collection_name = app.config.get("MONGO_LOG_COLLECTION", "app_logs")

    if not mongo_uri:
        return

    handler = MongoLogHandler(mongo_uri, db_name, collection_name)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)

    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(handler)


def get_audit_collection(app):
    mongo_uri = app.config.get("MONGO_URI")
    if not mongo_uri:
        return None
    db_name = app.config.get("MONGO_DB", "panaderia")
    collection_name = app.config.get("MONGO_AUDIT_COLLECTION", "audit_logs")
    client = _get_client(mongo_uri)
    return client[db_name][collection_name]


def write_audit_event(app, payload: dict):
    collection = get_audit_collection(app)
    if collection is None:
        return
    try:
        payload = dict(payload)
        payload.setdefault("timestamp", datetime.datetime.utcnow())
        collection.insert_one(payload)
    except Exception:
        pass
