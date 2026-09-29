"""Application settings module."""

from functools import cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",  # let docker-compose-only vars pass through unused
        env_file_encoding="utf-8",
    )

    solis_api_url: str = "https://www.soliscloud.com:13333"
    solis_api_base: str = "/v1/api/"
    solis_key_id: SecretStr = Field(validation_alias="SOLIS_KEY_ID")
    solis_key_secret: SecretStr = Field(validation_alias="SOLIS_KEY_SECRET")
    solis_inverter_sn: SecretStr = Field(validation_alias="SOLIS_INVERTER_SN")

    api_call_attempts: int = 5
    api_call_delay: int = 30  # seconds

    fallback_max_retry: int = 3
    fallback_retry_delay: int = 60  # seconds

    pingram_api_url: str = "https://api.eu.pingram.io"
    pingram_api_key: SecretStr = Field(validation_alias="PINGRAM_API_KEY")
    from_name: str = "Solis Energy Manager"
    destination_email: SecretStr = Field(validation_alias="DESTINATION_EMAIL")
    cc_email: SecretStr = Field(validation_alias="CC_EMAIL")

    # Open Meteo API settings
    open_meteo_api_url: str = "https://api.open-meteo.com/v1/forecast"
    home_latitude: SecretStr = Field(validation_alias="HOME_LATITUDE")
    home_longitude: SecretStr = Field(validation_alias="HOME_LONGITUDE")
    cutoff_hour: int = 14

    schedule_name: str = "daily_refresh"
    cron_schedule: str = "0 16 * * *"  # runs once every day at 4:00 PM


@cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]


if __name__ == "__main__":
    settings = get_settings()
    print(settings)
