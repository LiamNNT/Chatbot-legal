from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- General Application Settings ---
    app_env: str = "dev"
    port: int = 8000

    # --- Vector Store Configuration ---
    vector_backend: str = "qdrant"
    storage_dir: str = "./storage"
    
    # Qdrant Cloud settings
    qdrant_url: str = "https://2ee9a81c-be7d-484a-93cf-2f229545d6a4.us-east-1-1.aws.cloud.qdrant.io/"
    qdrant_api_key: str = ""
    qdrant_collection_name: str = "vietnamese_documents"
    
    # Dual-write mode: index to both Qdrant (vector) and OpenSearch (keyword) simultaneously
    enable_dual_index: bool = False

    # --- AI Model Configuration ---
    emb_model: str = "BAAI/bge-m3"
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    
    # --- Reranking Configuration ---
    use_reranking: bool = True  
    rerank_batch_size: int = 16  
    rerank_max_length: int = 512 
    rerank_top_k: int = 20  
    vietnamese_rerank_model: str = ""

    # --- OpenSearch Settings for BM25 ---
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_index: str = "rag_documents"
    opensearch_username: str = "admin"
    opensearch_password: str = "admin"
    opensearch_use_ssl: bool = False
    opensearch_verify_certs: bool = False

    # --- Hybrid Search Settings ---
    use_hybrid_search: bool = True 
    bm25_weight: float = 0.5     
    vector_weight: float = 0.5     
    rrf_rank_constant: int = 60 

    # --- LLM Configuration ---
    openai_api_key: str = "" 
    openai_base_url: str = ""  
    gemini_api_key: str = ""  
    llm_provider: str = "openai"  
    llm_model: str = "gpt-4o-mini"  
    llm_temperature: float = 0.0 
    llm_max_tokens: int = 2000 

    # --- 3-Tier Extraction Strategy ---
    tier2_model_id: str = "x-ai/grok-4.1-fast:free"  
    tier2_temperature: float = 0.1
    tier2_max_tokens: int = 2048
    tier3_model_id: str = "x-ai/grok-4.1-fast:free" 
    tier3_temperature: float = 0.0
    tier3_max_tokens: int = 4096

    # --- Neo4j Graph Database ---
    neo4j_uri: str = ""
    neo4j_username: str = "" 
    neo4j_password: str = ""
    neo4j_database: str = ""

    # --- Redis Configuration (for job state) ---
    redis_url: str = "redis://localhost:6379/0"

    # --- LlamaIndex Extraction Configuration ---
    use_llamaindex_extraction: bool = True  
    llama_cloud_api_key: str = "llx-hA9tHV3v481rmzAjnyTk14iOxjpG7lCjSO4R4s9dxPhCF10k" 
    llama_parse_gpt4o_mode: bool = True
    llama_parse_result_type: str = "markdown" 
    
    # --- Logging Configuration ---
    log_level: str = "INFO"

    # --- OpenRouter / VLM Configuration (optional) ---
    openrouter_api_key: str = "" 
    vlm_model: str = "" 

    # Pydantic model configuration to specify the source of the settings
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Create a singleton instance of the Settings class to be used across the application
settings = Settings()