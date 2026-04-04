# config.py — all tuneable values live here

SECRET_KEY = "dev-secret-change-in-production"
ALGORITHM  = "HS256"
TOKEN_EXPIRE_MINUTES = 60

DATABASE_URL = "sqlite:///./fintrack.db"

OLLAMA_URL   = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:7b"
