from typing import List
from pathlib import Path
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, Settings, Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.node_parser import SentenceSplitter
from app.config.settings import settings
from store.vector.faiss_store import get_faiss_vector_store, persist_faiss
from store.vector.chroma_store import get_chroma_vector_store

def _ensure_storage():
    Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)

def _prepare_service_context():
    Settings.embed_model = HuggingFaceEmbedding(model_name=settings.emb_model)
    Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=64)

def _load_documents(source_dir: str) -> List[Document]:
    reader = SimpleDirectoryReader(
        input_dir=source_dir,
        recursive=True,
        required_exts=['.txt', '.md', '.pdf', '.docx'],
        filename_as_id=True
    )
    return reader.load_data()

def _get_vector_store():
    backend = settings.vector_backend.lower()
    if backend == "faiss":
        return get_faiss_vector_store()
    elif backend == "chroma":
        return get_chroma_vector_store()
    else:
        raise ValueError(f"Unsupported VECTOR_BACKEND: {settings.vector_backend}")

def reindex_from_manifest(manifest) -> int:
    _ensure_storage()
    _prepare_service_context()

    docs = _load_documents(manifest.source_dir)
    if not docs:
        return 0

    vector_store = _get_vector_store()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_documents(docs, storage_context=storage_context, show_progress=True)

    # Persist docstore/indexstore for LlamaIndex
    persist_dir = Path(settings.storage_dir) / "li_storage"
    index.storage_context.persist(persist_dir=str(persist_dir))

    # Persist FAISS raw index (if used)
    if settings.vector_backend.lower() == "faiss":
        persist_faiss(vector_store)

    return len(docs)
