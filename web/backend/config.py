"""Configuration for the FastAPI backend."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_url: str = "postgresql://paranormal:paranormal@localhost:5433/paranormal_tracker"
    voyage_api_key: str = ""
    voyage_model: str = "voyage-4-large"
    voyage_api_url: str = "https://api.voyageai.com/v1/embeddings"

    # CORS origins for development
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()
