from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = "dev"
    port: int = 8000

    vector_backend: str = "faiss"  # faiss | chroma
    storage_dir: str = "./storage"

    emb_model: str = "intfloat/multilingual-e5-base"
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # optional

    chroma_persist_dir: str = "./storage/chroma"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()