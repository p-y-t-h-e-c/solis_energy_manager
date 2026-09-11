"""Application settings module."""

from functools import cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    solis_api_url: str = "https://www.soliscloud.com:13333"
    solis_api_base: str = "/v1/api/"
    solis_key_id: SecretStr
    solis_key_secret: SecretStr
    solis_inverter_sn: SecretStr

    api_call_attempts: int = 4
    api_call_delay: int = 5  # seconds
    schedule_name: str = "daily_refresh"
    cron_schedule: str = "0 0 * * *"  # runs once every day at 12:00 AM (midnight)


@cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]


if __name__ == "__main__":
    settings = get_settings()
    print(settings)
