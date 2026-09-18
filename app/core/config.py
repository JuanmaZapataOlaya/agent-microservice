from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    base_url: str
    portkey_api_key: str
    portkey_model: str
    embedding_model: str = "text-embedding-004"
    supabase_url: str
    supabase_service_role_key: str
    edge_shared_secret: str
    ingest_api_key: str
    session_ttl_minutes: int = Field(default=60, ge=1)
    top_k_results: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.72, ge=0, le=1)
    chunk_size: int = Field(default=800, ge=100)
    chunk_overlap: int = Field(default=120, ge=0)
    rate_limit_per_minute: int = Field(default=30, ge=1)
    log_level: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
