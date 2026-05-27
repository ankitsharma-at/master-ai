"""Central configuration - Supabase integrated."""
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    llm_provider: str = "anthropic"  # "anthropic", "openai", or "gemini"
    llm_model: str = "claude-sonnet-4-20250514"
    supabase_url: str = ""
    supabase_service_key: str = ""
    embedding_model: str = "all-MiniLM-L6-v2"
    tools_dir: str = "./tools"
    reuse_threshold: float = 0.85
    adapt_threshold: float = 0.60
    sandbox_timeout_seconds: int = 30
    sandbox_memory_limit: str = "256m"
    sandbox_cpu_limit: float = 0.5
    docker_image: str = "python:3.11-slim"
    max_debug_iterations: int = 3
    min_reliability_score: int = 75
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = "change-me"

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()
