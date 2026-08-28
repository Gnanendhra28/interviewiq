from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development" # "development", "test", "staging", "production"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "dev_secret_key_change_in_production_32_chars_min"
    
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "InterviewIQ API"
    
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Database
    POSTGRES_USER: str = "interviewiq"
    POSTGRES_PASSWORD: str = "interviewiq_dev_pass"
    POSTGRES_DB: str = "interviewiq_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5433
    DATABASE_URL: str = "postgresql+asyncpg://interviewiq:interviewiq_dev_pass@localhost:5433/interviewiq_db"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"

    # Distributed Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = True
    AUTH_RATE_LIMIT_PER_MIN: int = 10
    UPLOAD_RATE_LIMIT_PER_MIN: int = 10
    AI_RATE_LIMIT_PER_MIN: int = 20
    DEFAULT_RATE_LIMIT_PER_MIN: int = 100

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
    STORAGE_PROVIDER: str = "local" # "local" or "gcs"
    STORAGE_LOCAL_PATH: str = "./data/uploads"
    GCS_BUCKET_NAME: str = "interviewiq-resumes-prod"
    MAX_RESUME_SIZE_BYTES: int = 10 * 1024 * 1024 # 10 MB

    # Text Quality Validation Configurable Thresholds
    RESUME_MIN_EXTRACTED_TEXT_CHARS: int = 100
    RESUME_MAX_NON_PRINTABLE_RATIO: float = 0.15

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

    def validate_production_configuration(self) -> None:
        """
        Production fail-fast startup validation for mandatory operational security standards.
        """
        if self.ENVIRONMENT in ("production", "staging"):
            if self.SECRET_KEY == "dev_secret_key_change_in_production_32_chars_min" or len(self.SECRET_KEY) < 32:
                raise ValueError(f"Insecure SECRET_KEY configured for environment '{self.ENVIRONMENT}'. Must be >= 32 characters and non-default.")
            
            if "interviewiq_dev_pass" in self.DATABASE_URL:
                raise ValueError(f"Insecure development password detected in DATABASE_URL for environment '{self.ENVIRONMENT}'.")

            if self.STORAGE_PROVIDER == "gcs" and not self.GCS_BUCKET_NAME:
                raise ValueError("GCS_BUCKET_NAME is required when STORAGE_PROVIDER='gcs'.")

            if "*" in self.ALLOWED_ORIGINS:
                raise ValueError("Wildcard '*' ALLOWED_ORIGINS forbidden in staging/production when credentials are enabled.")


settings = Settings()
