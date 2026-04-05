from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "agentic-analytics-copilot"
    app_env: str = "local"
    bootstrap_on_startup: bool = True
    duckdb_path: str = "data/structured/operations.duckdb"
    chroma_path: str = "data/vector/chroma"
    chroma_collection_name: str = "ops_knowledge_base"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-4.1-mini"
    jwt_secret: str = "local-demo-secret"
    jwt_algorithm: str = "HS256"
    rate_limit_per_minute: int = 10
    hybrid_search_rrf_k: int = 60
    hybrid_search_vector_candidates: int = 20
    hybrid_search_keyword_candidates: int = 20
    retrieval_final_limit: int = 5
    enable_reranker: bool = True
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    semantic_cache_path: str = "data/cache/semantic_cache.sqlite"
    semantic_cache_similarity_threshold: float = 0.95
    observability_db_path: str = "data/cache/observability.sqlite"
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
