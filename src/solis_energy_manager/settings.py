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

    pushstaq_api_url: str = "https://www.pushstaq.com/api/push/"
    pushstaq_api_key: SecretStr

    api_call_attempts: int = 5
    api_call_delay: int = 30  # seconds

    fallback_max_retry: int = 3
    fallback_retry_delay: int = 60  # seconds

    schedule_name: str = "daily_refresh"
    cron_schedule: str = "0 0 * * *"  # runs once every day at 12:00 AM (midnight)


@cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]


if __name__ == "__main__":
    settings = get_settings()
    print(settings)
