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

    # LLM sentiment analysis
    anthropic_api_key: str = ""
    sentiment_model_batch: str = "claude-haiku-4-5"
    sentiment_model_deep: str = "claude-sonnet-5"
    sentiment_max_daily_calls: int = 50
    sentiment_cache_hours: int = 24
    finnhub_api_key: str = ""

    model_config = {"env_prefix": "TRADING_"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
