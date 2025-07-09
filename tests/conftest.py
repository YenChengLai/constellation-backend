import os

import motor.motor_asyncio
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from packages.shared_utils.database import get_db
from services.auth_service.app.main import app

TEST_MONGO_URI = os.getenv("TEST_MONGODB_URI", "mongodb://localhost:27017/")
TEST_DB_NAME = "constellation_test_db"


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """
    A fixture that provides a clean, isolated database for each test function.
    It creates a new client, yields the database object, and then cleans up.
    """
    # 1. Setup: Create a new client for each test
    db_client = motor.motor_asyncio.AsyncIOMotorClient(TEST_MONGO_URI)
    the_db = db_client[TEST_DB_NAME]

    # Drop the database to ensure a clean state before the test
    await db_client.drop_database(the_db)

    # 2. Yield the database object for the test to use
    yield the_db

    # 3. Teardown: Clean up the database and close the client connection
    await db_client.drop_database(the_db)
    db_client.close()


@pytest_asyncio.fixture(scope="function")
async def client(test_db: motor.motor_asyncio.AsyncIOMotorDatabase) -> AsyncClient:
    """
    A fixture that provides an httpx.AsyncClient for making API requests.
    It depends on the `test_db` fixture to get an isolated database.
    """
    # Override the app's get_db dependency to use our isolated test_db
    app.dependency_overrides[get_db] = lambda: test_db

    # Create the client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clear the dependency override after the test
    app.dependency_overrides.clear()
