from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "agentic-analytics-copilot"
    app_env: str = "local"
    duckdb_path: str = "data/structured/operations.duckdb"
    chroma_path: str = "data/vector/chroma"
    chroma_collection_name: str = "ops_knowledge_base"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-4.1-mini"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
