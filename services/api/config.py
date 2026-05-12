from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Bhav API"
    app_version: str = "0.1.0"
    debug: bool = True

    database_url: str = "postgresql://postgres:postgres@localhost:5434/bhav"
    redis_url: str = "redis://localhost:6381"

    cors_origins: list[str] = ["http://localhost:3000"]

    market_data_provider: str = "yfinance"
    scan_universe: str = "NSE_500"
    intraday_enabled: bool = False
    commentary_top_n: int = 20

    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-6"

    newsapi_key: str = ""
    alphavantage_api_key: str = ""

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    alert_min_score: int = 80

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
