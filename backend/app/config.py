from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Trading Signal"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/trading"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/trading"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 1440
    algorithm: str = "HS256"

    # signal thresholds
    buy_threshold: float = 0.3
    sell_threshold: float = -0.3

    model_config = {"env_prefix": "TRADING_"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
