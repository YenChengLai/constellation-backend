from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Shared application settings, loaded from the .env file.
    """

    SECRET_KEY: str
    ALGORITHM: str
    MONGODB_URI: str
    ADMIN_EMAIL: EmailStr

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
