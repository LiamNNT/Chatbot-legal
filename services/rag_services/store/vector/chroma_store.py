from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb
from app.config.settings import settings

_chroma_store = None

def get_chroma_vector_store() -> ChromaVectorStore:
    global _chroma_store
    if _chroma_store is not None:
        return _chroma_store
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    collection = client.get_or_create_collection("rag_collection")
    _chroma_store = ChromaVectorStore(chroma_collection=collection)
    return _chroma_store
