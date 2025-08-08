# scripts/seed_database.py

import asyncio
import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# 暫時直接從 service 引入 Pydantic 模型
from services.expense_service.app.models import CategoryCreate

load_dotenv()

# --- ✨ 使用 Emoji 文字代碼來定義預設資料 ---
DEFAULT_CATEGORIES = [
    {"name": "餐飲", "type": "expense", "icon": ":hamburger:"},
    {"name": "交通", "type": "expense", "icon": ":car:"},
    {"name": "購物", "type": "expense", "icon": ":shopping_bags:"},
    {"name": "娛樂", "type": "expense", "icon": ":clapper:"},
    {"name": "居家", "type": "expense", "icon": ":house:"},
    {"name": "薪資", "type": "income", "icon": ":moneybag:"},
    {"name": "投資", "type": "income", "icon": ":chart_with_upwards_trend:"},
]


async def seed_data():
    """Connects to the DB and seeds the default categories."""
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        print("❌ MONGODB_URI not found in .env file. Aborting.")
        return

    client = AsyncIOMotorClient(mongodb_uri)
    db = client.constellation_db

    print("🌱 Starting database seeding...")

    categories_collection = db.categories

    for category_data in DEFAULT_CATEGORIES:
        exists = await categories_collection.find_one(
            {"name": category_data["name"], "type": category_data["type"], "user_id": None}
        )

        if exists:
            # 如果已存在，可以選擇更新它的圖示
            await categories_collection.update_one({"_id": exists["_id"]}, {"$set": {"icon": category_data["icon"]}})
            print(f"   ~ Updated icon for category '{category_data['name']}'.")
        else:
            category = CategoryCreate(**category_data)
            await categories_collection.insert_one(category.model_dump())
            print(f"   + Created default category: '{category_data['name']}'")

    print("✅ Database seeding complete.")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed_data())
