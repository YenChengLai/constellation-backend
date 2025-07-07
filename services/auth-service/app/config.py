from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Loads settings from environment variables.
    """
    APP_NAME: str = "Constellation Auth Service"
    ADMIN_EMAIL: str = "admin@example.com"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()