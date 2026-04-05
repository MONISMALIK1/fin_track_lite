# config.py — all tuneable values live here
import os

class Settings:
    """Central configuration object for the application."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    ALGORITHM = "HS256"
    TOKEN_EXPIRE_MINUTES = 60
    
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fintrack.db")
    
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = "qwen2.5:7b"
    
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

settings = Settings()

