import os
from datetime import timezone

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

# It's a good practice to read the DB connection string and name from environment variables.
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DB_NAME = "constellation_db"


class DBClient:
    """
    A singleton-like class to manage the database client connection.
    """

    client: AsyncIOMotorClient | None = None


db_client = DBClient()


async def get_db() -> AsyncIOMotorDatabase:
    """
    FastAPI dependency to get the async database instance.
    This function will be called for each request that needs a DB connection.
    """
    if db_client.client is None:
        # This should ideally only happen once, at application startup.
        # We will manage this with startup/shutdown events in main.py
        raise RuntimeError("Database client has not been initialized.")
    return db_client.client[DB_NAME]


async def connect_to_mongo():
    """
    Event handler for application startup. Connects to the database.
    """
    print("Connecting to MongoDB...")
    db_client.client = AsyncIOMotorClient(MONGODB_URI, tz_aware=True, tzinfo=timezone.utc)
    print("Connection successful.")


async def close_mongo_connection():
    """
    Event handler for application shutdown. Closes the database connection.
    """
    if db_client.client:
        print("Closing MongoDB connection...")
        db_client.client.close()
        print("Connection closed.")
