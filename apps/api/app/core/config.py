from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "dev_secret_key_change_in_production_32_chars_min"
    
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "InterviewIQ API"
    
    ALLOWED_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    # Database
    POSTGRES_USER: str = "interviewiq"
    POSTGRES_PASSWORD: str = "interviewiq_dev_pass"
    POSTGRES_DB: str = "interviewiq_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql+asyncpg://interviewiq:interviewiq_dev_pass@localhost:5432/interviewiq_db"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI Provider Configuration
    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Model-Aware Embedding Layer Configuration (Initial Production Default: gemini-embedding-2)
    EMBEDDING_PROVIDER: str = "gemini"
    EMBEDDING_MODEL: str = "gemini-embedding-2"
    EMBEDDING_DIMENSION: int = 768
    EMBEDDING_VERSION: str = "v1"

    # Storage Provider Configuration
    STORAGE_PROVIDER: str = "local"
    STORAGE_LOCAL_PATH: str = "./data/uploads"

    # Authentication & Session Security Policies
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Interview Lifecycle Policies (Explicitly Separated)
    INTERVIEW_INACTIVITY_TIMEOUT_MINUTES: int = 30
    INTERVIEW_MAX_DURATION_MINUTES: int = 90

    # RAG Retrieval Settings
    DEFAULT_TOP_K_RETRIEVAL: int = 5
    MIN_RELEVANCE_SCORE: float = 0.70

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
