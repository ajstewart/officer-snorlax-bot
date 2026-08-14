"""Settings for the bot."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    """Bot settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        ignore_empty_env_vars=True,
        extra="ignore",
    )

    token: SecretStr
    database: str = "bot.db"
    default_open_message: str = "**Used the Poké Flute and Snorlax woke up!**"
    default_close_message: str = "**Snorlax is blocking the path!**"
    default_tz: str = "Australia/Sydney"
    default_warning_time: int = 15
    default_inactive_time: int = 5
    default_delay_time: int = 5
    default_prefix: str = "!"
    test_guild: int | None = None
    log_level: str = "INFO"


bot_settings = BotSettings()
