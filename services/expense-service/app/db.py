import os

from pymongo import MongoClient
from pymongo.database import Database


def get_db() -> Database:
    client: MongoClient = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
    return client["expense_tracker"]
