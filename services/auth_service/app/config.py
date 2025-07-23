# services/auth_service/app/config.py

from packages.shared_utils.config import Settings as BaseSettings


class AuthServiceSettings(BaseSettings):
    """
    Settings specific to the Authentication Service.
    It inherits all settings from the shared BaseSettings and adds its own.
    """

    APP_NAME: str = "Constellation Auth Service"
    # Future auth-service specific variables can be added here.


# Create an instance of the service-specific settings
settings = AuthServiceSettings()
