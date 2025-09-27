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

    # --- ChromaDB Specific Settings ---
    chroma_persist_dir: str = "./storage/chroma" # Directory for ChromaDB persistence

    # --- Logging Configuration ---
    log_level: str = "INFO"

    # Pydantic model configuration to specify the source of the settings
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Create a singleton instance of the Settings class to be used across the application
settings = Settings()