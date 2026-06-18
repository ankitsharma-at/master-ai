"""Central configuration - Supabase integrated."""
from pydantic_settings import BaseSettings
from functools import lru_cache
from key_manager import APIKeyManager
key_manager = APIKeyManager()

class Settings(BaseSettings):
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    # google_api_key: str = ""
    @property
    def google_api_key(self):
        return key_manager.get_key()
    gemini_key_1: str = ""
    gemini_key_2: str = ""
    gemini_key_3: str = ""
    gemini_key_4: str = ""
    
    llm_provider: str = "gemini"  # "anthropic", "openai", or "gemini"
    llm_model: str = "gemini-flash-latest"
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_anon_key: str = ""
    embedding_model: str = "all-MiniLM-L6-v2"
    tools_dir: str = "./tools"
    reuse_threshold: float =  0.65
    adapt_threshold: float =  0.45
    enable_direct_llm: bool = True  # Enable direct LLM for simple tasks
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
