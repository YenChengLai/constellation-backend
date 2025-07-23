# packages/shared_utils/database.py

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

# ✨ 修正點：從新的共享 config 檔案引入 settings
from packages.shared_utils.config import settings

client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None


async def connect_to_mongo():
    global client, db
    print("Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client.constellation_db
    print("Successfully connected to MongoDB.")


async def close_mongo_connection():
    global client
    if client:
        client.close()
        print("MongoDB connection closed.")


async def get_db() -> AsyncIOMotorDatabase:
    if db is None:
        await connect_to_mongo()
    return db
