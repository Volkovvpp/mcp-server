from datetime import datetime
from pymongo import MongoClient

from src.core.config import settings


def get_mongo_client() -> MongoClient:
    mongo_user = settings.MONGO_USER
    mongo_password = settings.MONGO_PASSWORD
    mongo_host = settings.MONGO_HOST
    mongo_port = settings.MONGO_PORT
    mongo_db = settings.MONGO_DB

    mongo_uri = (
        f"mongodb://{mongo_user}:{mongo_password}"
        f"@{mongo_host}:{mongo_port}/{mongo_db}?authSource=admin"
    )
    return MongoClient(mongo_uri)


_client = get_mongo_client()
mongodb = _client[settings.MONGO_DB]

mcp_metrics_collection = mongodb["mcp_metrics"]

def save_metric_to_mongo(data: dict):
    data["timestamp"] = datetime.utcnow()
    mcp_metrics_collection.insert_one(data)
