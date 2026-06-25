from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://app:app@localhost:5432/app"
    session_secret: str = "dev-insecure-session-secret-change-me"
    encryption_key: str = ""  # Fernet key; generated in dev if blank
    initial_admin_username: str = "admin"
    initial_admin_password: str = "changeme"
    # Optional extra admin accounts, seeded idempotently at boot.
    # Format: "user1:pass1,user2:pass2". Existing usernames are never overwritten.
    extra_admins: str = ""
    prep_window_days: int = 8
    display_timezone: str = "Europe/London"
    content_dir: str = "content"


@lru_cache
def get_settings() -> Settings:
    return Settings()
