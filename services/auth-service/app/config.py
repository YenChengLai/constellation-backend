# File: services/auth-service/app/config.py
# Description: Corrected configuration for the Auth service.

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Loads all required settings from environment variables defined in .env
    """

    # --- Declare all variables from your .env file here ---

    # Database Configuration
    MONGODB_URI: str

    # JWT Authentication
    SECRET_KEY: str
    ALGORITHM: str

    # Application-specific
    APP_NAME: str = "Constellation Auth Service"
    ADMIN_EMAIL: str

    # Inter-service Communication (for future use)
    # We make this optional by allowing None and providing a default
    EXPENSE_SERVICE_URL: str | None = None

    # This tells pydantic-settings where to find the .env file.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Create a single instance to be imported in other modules
settings = Settings()