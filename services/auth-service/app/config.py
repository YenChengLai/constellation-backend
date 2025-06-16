import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 從環境變數讀取，並提供預設值
    SECRET_KEY: str = "your-secret-key"
    ALGORITHM: str = "HS256"
    ADMIN_EMAIL: str = "admin@example.com"
    EXPENSE_SERVICE_URL: str = "http://127.0.0.1:8001"
    # MONGODB_URI: str = "mongodb://localhost:27017/" # 也可以放這裡

    class Config:
        # 如果你在專案根目錄有 .env 檔案，它會自動讀取
        env_file = ".env"


# 建立一個全域實例，方便在其他地方 import
settings = Settings()
