import os
from dataclasses import dataclass


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "PetCare MCP API")
    POSTGRES_URL: str = os.getenv(
        "POSTGRES_URL",
        "postgresql+asyncpg://petcare-admin:supersecret@postgres:5432/petcare",
    )
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "minio:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "petcare")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "petcare123")
    MINIO_BUCKET_PRIVATE: str = os.getenv("MINIO_BUCKET_PRIVATE", "petcare-private")
    MINIO_USE_SSL: bool = _get_bool("MINIO_USE_SSL", False)
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    AUTH_DEMO_PASSWORD: str = os.getenv("AUTH_DEMO_PASSWORD", "petcare-demo-password")
    REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "5"))
    DEFAULT_LLM: str = os.getenv("DEFAULT_LLM", "gemma")
    GEMMA_ENDPOINT: str | None = os.getenv("GEMMA_ENDPOINT")
    GEMMA_API_KEY: str | None = os.getenv("GEMMA_API_KEY")
    GEMMA_TIMEOUT_SECONDS: int = int(os.getenv("GEMMA_TIMEOUT_SECONDS", "5"))


settings = Settings()
