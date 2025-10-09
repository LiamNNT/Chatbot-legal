# app/config/settings.py
#
# Description:
# This module defines and manages all configuration settings for the RAG service.
# It uses Pydantic's BaseSettings to load configuration from environment variables
# or a .env file, providing a centralized and type-safe way to handle settings.
#
# Key Responsibilities:
# - Define the application's configuration schema.
# - Load settings from environment variables or a specified .env file.
# - Provide a singleton `settings` object for easy access throughout the application.

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Defines the application's configuration settings.
    Pydantic automatically reads values from environment variables or the .env file.
    """
    # --- General Application Settings ---
    app_env: str = "dev"
    port: int = 8000

    # --- Vector Store Configuration ---
    vector_backend: str = "faiss"  # Can be 'faiss' or 'chroma'
    storage_dir: str = "./storage" # Directory to store indices and other data

    # --- AI Model Configuration ---
    emb_model: str = "intfloat/multilingual-e5-base" # The embedding model to use
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # Optional reranker model
    
    # --- Reranking Configuration ---
    use_reranking: bool = True  # Enable reranking with cross-encoder
    rerank_batch_size: int = 16  # Batch size for reranking operations
    rerank_max_length: int = 512  # Maximum input length for reranker
    rerank_top_k: int = 20  # Number of initial candidates to retrieve for reranking
    vietnamese_rerank_model: str = ""  # Optional Vietnamese-specific model

    # --- ChromaDB Specific Settings ---
    chroma_persist_dir: str = "./storage/chroma" # Directory for ChromaDB persistence

    # --- OpenSearch Settings for BM25 ---
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_index: str = "rag_documents"
    opensearch_username: str = "admin"
    opensearch_password: str = "admin"
    opensearch_use_ssl: bool = False
    opensearch_verify_certs: bool = False

    # --- Hybrid Search Settings ---
    use_hybrid_search: bool = True  # Enable hybrid (vector + BM25) search
    bm25_weight: float = 0.5       # Weight for BM25 scores in fusion
    vector_weight: float = 0.5      # Weight for vector scores in fusion
    rrf_rank_constant: int = 60     # RRF rank constant (typically 60)

    # --- Logging Configuration ---
    log_level: str = "INFO"

    # Pydantic model configuration to specify the source of the settings
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Create a singleton instance of the Settings class to be used across the application
settings = Settings()