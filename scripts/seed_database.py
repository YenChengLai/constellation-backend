# scripts/seed_database.py

import asyncio
import os

# 這裡我們需要一種方式讀取 .env 的 MONGODB_URI
# 為了簡單起見，我們先直接讀取，未來可以整合進共享的 config
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# 暫時直接從 service 引入 Pydantic 模型，未來可以考慮讓共享模型更完善
from services.expense_service.app.models import CategoryCreate

load_dotenv()  # 載入根目錄的 .env 檔案

# --- 要寫入的預設資料 ---

DEFAULT_CATEGORIES = [
    {"name": "餐飲", "type": "expense", "icon": "🍔"},
    {"name": "交通", "type": "expense", "icon": "🚗"},
    {"name": "購物", "type": "expense", "icon": "🛍️"},
    {"name": "娛樂", "type": "expense", "icon": "🎬"},
    {"name": "居家", "type": "expense", "icon": "🏠"},
    {"name": "薪資", "type": "income", "icon": "💰"},
    {"name": "投資", "type": "income", "icon": "📈"},
]


async def seed_data():
    """Connects to the DB and seeds the default categories."""
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        print("❌ MONGODB_URI not found in .env file. Aborting.")
        return
    print(mongodb_uri)
    client = AsyncIOMotorClient(mongodb_uri)
    db = client.constellation_db  # 假設資料庫名稱為 constellation_db

    print("🌱 Starting database seeding...")

    categories_collection = db.categories

    for category_data in DEFAULT_CATEGORIES:
        # 檢查這個預設分類是否已經存在
        # 預設分類沒有 user_id
        exists = await categories_collection.find_one(
            {"name": category_data["name"], "type": category_data["type"], "user_id": None}
        )

        if exists:
            print(f"   - Category '{category_data['name']}' already exists. Skipping.")
        else:
            # Pydantic 模型會幫我們驗證資料格式
            category = CategoryCreate(**category_data)
            await categories_collection.insert_one(category.model_dump())
            print(f"   + Created default category: '{category_data['name']}'")

    print("✅ Database seeding complete.")
    client.close()


if __name__ == "__main__":
    # 允許這個腳本被直接執行
    asyncio.run(seed_data())
