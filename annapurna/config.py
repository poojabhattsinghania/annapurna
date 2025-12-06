"""Configuration management using Pydantic settings"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    database_url: str
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "annapurna"
    database_user: str
    database_password: str

    # LLM APIs
    google_api_key: str  # For Gemini
    gemini_api_key: Optional[str] = None  # Alias for backwards compatibility
    openai_api_key: Optional[str] = None

    # LLM Model Selection
    gemini_model_lite: str = "gemini-2.0-flash-8b"  # For simple structured tasks (cheapest - 8B params)
    gemini_model_default: str = "gemini-2.0-flash"  # For complex reasoning (workhorse)
    gemini_model_complex: str = "gemini-2.0-flash"  # For most complex tasks

    # Embedding Model
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant Vector Database
    qdrant_url: str = "http://localhost:6333"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use google_api_key as gemini_api_key if not explicitly set
        if not self.gemini_api_key and self.google_api_key:
            self.gemini_api_key = self.google_api_key

    # Application
    environment: str = "development"
    log_level: str = "INFO"
    api_version: str = "v1"

    # Scraping
    youtube_api_key: Optional[str] = None
    scraper_user_agent: str = "Mozilla/5.0 (compatible; AnnapurnaBot/1.0)"
    scraper_rate_limit: int = 10

    # LLM Processing
    llm_batch_size: int = 10
    llm_timeout: int = 30
    auto_tag_confidence_threshold: float = 0.7

    # Duplicate Detection
    similarity_title_threshold: float = 0.85
    similarity_ingredient_threshold: float = 0.70
    similarity_embedding_threshold: float = 0.90

    class Config:
        env_file = ".env"
        case_sensitive = False


# Singleton instance
settings = Settings()
