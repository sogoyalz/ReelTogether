from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Movie Analytics API"
    APP_VERSION: str = "0.2.0"
    API_V1_PREFIX: str = "/api"

    DATABASE_URL: str = "sqlite:///./movie_analytics.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    TMDB_API_KEY: str = ""
    YOUTUBE_API_KEY: str = ""
    OMDB_API_KEY: str = ""
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    SECRET_KEY: str = "change-me-in-production"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
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


settings = Settings()
