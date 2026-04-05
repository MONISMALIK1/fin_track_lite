# config.py — all tuneable values live here

import os
from functools import lru_cache


class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    ALGORITHM: str = "HS256"
    TOKEN_EXPIRE_MINUTES: int = 60

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./fintrack.db"
    )

    OLLAMA_ENABLED: bool = os.getenv("OLLAMA_ENABLED", "false").lower() == "true"
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
