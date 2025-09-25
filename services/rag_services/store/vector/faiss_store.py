from pathlib import Path
from llama_index.vector_stores.faiss import FaissVectorStore
import faiss
from app.config.settings import settings

_INDEX_PATH = Path(settings.storage_dir) / "faiss.index"
_faiss_store = None

def get_faiss_vector_store() -> FaissVectorStore:
    """
    Create/load a FAISS index and wrap it by LlamaIndex FaissVectorStore.
    NOTE: Do NOT pass index_path (not supported in your adapter version).
    """
    global _faiss_store
    if _faiss_store is not None:
        return _faiss_store

    # Default dim = 768 for intfloat/multilingual-e5-base
    # If you change embedding model, update this dim accordingly.
    dim = 768

    if _INDEX_PATH.exists():
        index = faiss.read_index(str(_INDEX_PATH))
    else:
        # IP + normalized embeddings ≈ cosine similarity
        index = faiss.IndexFlatIP(dim)

    _faiss_store = FaissVectorStore(faiss_index=index)
    return _faiss_store

def persist_faiss(store: FaissVectorStore):
    """
    Explicitly persist the FAISS index to disk.
    """
    idx = store._faiss_index  # type: ignore
    faiss.write_index(idx, str(_INDEX_PATH))
