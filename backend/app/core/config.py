import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"

    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://aura_admin:aura_secure_dev_pass@localhost:5432/aura_db"
    
    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security Settings
    SECRET_KEY: str = "aura_super_secret_signing_key_change_me_in_prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Ingestion & Data Directory Setup
    UPLOAD_DIR: str = "data/uploads"
    DUCKDB_PATH: str = "data/duckdb/aura_analytics.db"

    # LLM Integrations
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    GEMINI_API_KEY: Optional[str] = None
    
    # AI Cost Optimization
    AI_BUDGET_LIMIT_USD: float = 10.0  # Daily budget threshold
    LLM_COST_PER_1K_INPUT_TOKENS: float = 0.00015  # Google Gemini Flash-level approximation
    LLM_COST_PER_1K_OUTPUT_TOKENS: float = 0.0006

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(self.DUCKDB_PATH), exist_ok=True)


settings = Settings()
