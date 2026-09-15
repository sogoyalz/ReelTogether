from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    APP_NAME: str = "ReelTogether API"
    APP_VERSION: str = "0.2.0"
    API_V1_PREFIX: str = "/api"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "sqlite:///./movie_analytics.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    TMDB_API_KEY: str = ""
    YOUTUBE_API_KEY: str = ""
    OMDB_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_CHAT_MODEL: str = "gpt-4.1-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_CHAT_MODEL: str = "claude-3-5-sonnet-latest"
    AI_CHAT_PROVIDER: str = "openai"
    ENABLE_ASSISTANT_AI: bool = False
    ASSISTANT_AI_CALLS_PER_HOUR: int = Field(60, ge=1, le=1000)
    USE_LIGHTWEIGHT_SENTIMENT: bool = True
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]
    TRUSTED_HOSTS: list[str] = [
        "localhost",
        "127.0.0.1",
    ]
    PROXY_SHARED_SECRET: str = ""
    ENABLE_USER_FEATURES: bool = False
    ENABLE_RAG: bool = False
    ENABLE_DOCS: bool = True
    ENABLE_STARTUP_SYNC: bool = True
    ENABLE_JOB_WORKER: bool = True
    ENABLE_PERIODIC_SYNC: bool = False
    ENABLE_RATE_LIMIT: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 120
    RATE_LIMIT_BURST_REQUESTS: int = 20
    ENABLE_GZIP: bool = True
    STARTUP_SYNC_TIMEOUT_SECONDS: int = 900
    STARTUP_SYNC_ASYNC: bool = True
    AUTO_CREATE_TABLES: bool = True

    SECRET_KEY: str = "change-me-in-production"
    ADMIN_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def youtube_api_configured(self) -> bool:
        return bool(self.YOUTUBE_API_KEY.strip())

    @property
    def omdb_api_configured(self) -> bool:
        return bool(self.OMDB_API_KEY.strip())

    @property
    def tmdb_api_configured(self) -> bool:
        return bool(self.TMDB_API_KEY.strip())

    @property
    def openai_api_configured(self) -> bool:
        return bool(self.OPENAI_API_KEY.strip())

    @property
    def anthropic_api_configured(self) -> bool:
        return bool(self.ANTHROPIC_API_KEY.strip())

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def docs_enabled(self) -> bool:
        return self.ENABLE_DOCS and not self.is_production


settings = Settings()
