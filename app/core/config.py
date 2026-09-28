"""
Central app configuration. Reads from environment variables / .env file.
Nothing else in the codebase should read os.environ directly — always
import `settings` from here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str
    ENV: str

    # --- PostgreSQL ---
    DATABASE_URL: str

    # --- Qdrant ---
    QDRANT_URL: str
    QDRANT_API_KEY: str
    QDRANT_COLLECTION: str

    EMBEDDING_PROVIDER: str = "fastembed"     
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIM: int = 384                   
    EMBEDDING_API_KEY: str | None = None
    EMBEDDING_BASE_URL: str | None = None

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 20

    PARENT_CHUNK_SIZE: int = 2000
    PARENT_CHUNK_OVERLAP: int = 200
    CHILD_CHUNK_SIZE: int = 400
    CHILD_CHUNK_OVERLAP: int = 50

    # --- JWT ---
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # --- CORS ---
    FRONTEND_ORIGIN: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()