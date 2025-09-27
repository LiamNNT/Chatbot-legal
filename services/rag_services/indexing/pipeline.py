# indexing/pipeline.py
#
# Description:
# This module defines the data indexing pipeline for the RAG service. It orchestrates
# the process of loading documents, parsing them into text chunks (nodes), generating
# vector embeddings, and storing them in the configured vector store (Faiss or Chroma).
#
# Key Responsibilities:
# - Reading various document types (.txt, .md, .pdf, .docx) from a source directory.
# - Configuring the embedding model and node parser (text splitter).
# - Building a LlamaIndex VectorStoreIndex from the documents.
# - Persisting the index and associated storage contexts to disk for later use.

from operator import index
from typing import List
from pathlib import Path

# LlamaIndex core components for building the RAG pipeline
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, Settings, Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.node_parser import SentenceSplitter

# Application-specific configurations and vector store handlers
from app.config.settings import settings
from store.vector.faiss_store import get_faiss_vector_store, persist_faiss
from store.vector.chroma_store import get_chroma_vector_store

def _ensure_storage():
    """Ensures that the primary storage directory exists."""
    Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)

def _prepare_service_context():
    """
    Configures the global LlamaIndex Settings for the indexing process.
    This sets up the embedding model and the text splitter (node parser).
    """
    Settings.embed_model = HuggingFaceEmbedding(model_name=settings.emb_model)
    Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=64)

def _load_documents(source_dir: str) -> List[Document]:
    """
    Loads all supported documents from the specified source directory.

    Args:
        source_dir (str): The path to the directory containing documents.

    Returns:
        List[Document]: A list of LlamaIndex Document objects.
    """
    reader = SimpleDirectoryReader(
        input_dir=source_dir,
        recursive=True,
        required_exts=['.txt', '.md', '.pdf', '.docx'],
        filename_as_id=True
    )
    return reader.load_data()

def _get_vector_store():
    """
    Factory function to get the vector store instance based on the application's configuration.

    Raises:
        ValueError: If an unsupported vector backend is configured.

    Returns:
        An instance of the configured vector store (e.g., FaissVectorStore or ChromaVectorStore).
    """
    backend = settings.vector_backend.lower()
    if backend == "faiss":
        return get_faiss_vector_store()
    elif backend == "chroma":
        return get_chroma_vector_store()
    else:
        raise ValueError(f"Unsupported VECTOR_BACKEND: {settings.vector_backend}")

def reindex_from_manifest(manifest) -> int:
    """
    The main function for the re-indexing process. It orchestrates all steps
    from loading documents to persisting the final index.

    Args:
        manifest: A manifest object containing specifications for the indexing job.

    Returns:
        int: The number of documents successfully indexed.
    """
    _ensure_storage()
    _prepare_service_context()

    docs = _load_documents(manifest.source_dir)
    if not docs:
        return 0

    # Set up the vector store and storage context
    vector_store = _get_vector_store()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Create the index from documents. This is the most computationally expensive step.
    index = VectorStoreIndex.from_documents(docs, storage_context=storage_context, show_progress=True)

    # Persist the LlamaIndex storage context (docstore, indexstore)
    persist_dir = Path(settings.storage_dir) / "li_storage"
    index.storage_context.persist(persist_dir=str(persist_dir))

    # If using Faiss, explicitly persist the raw Faiss index to disk
    if settings.vector_backend.lower() == "faiss":
        persist_faiss(vector_store)

    return len(docs)