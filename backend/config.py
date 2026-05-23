from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # App
    app_name: str = "Nova Platform"
    app_env: str = "development"
    backend_port: int = 8000

    # Groq
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    # Database
    database_url: str = "postgresql://nova_user:nova_pass@localhost:5432/nova_db"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # JWT
    jwt_secret: str = "nova_super_secret_jwt_key_change_in_production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"

    # Datasets
    dataset_path: str = "../Dataset"

    # CORS
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
