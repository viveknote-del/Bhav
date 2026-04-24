from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "{{PROJECT_DISPLAY_NAME}} API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Auth
    jwt_secret: str
    jwt_algorithm: str = "HS256"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # AI (optional)
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
