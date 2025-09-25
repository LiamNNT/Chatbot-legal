from typing import List, Optional
from pathlib import Path
from app.api.schemas.search import SearchRequest, SearchHit
from app.api.schemas.common import SourceMeta, CitationSpan
from app.config.settings import settings

from llama_index.core import VectorStoreIndex, StorageContext, Settings, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from store.vector.faiss_store import get_faiss_vector_store
from store.vector.chroma_store import get_chroma_vector_store

try:
    from sentence_transformers import CrossEncoder
except Exception:
    CrossEncoder = None

_index = None
_cross_encoder = None

def _ensure_settings():
    Settings.embed_model = HuggingFaceEmbedding(model_name=settings.emb_model)

def _get_vector_store():
    if settings.vector_backend.lower() == "faiss":
        return get_faiss_vector_store()
    return get_chroma_vector_store()

def _load_or_create_index():
    global _index
    if _index is not None:
        return _index

    _ensure_settings()
    vector_store = _get_vector_store()

    persist_dir = Path(settings.storage_dir) / "li_storage"
    storage_context = StorageContext.from_defaults(
        persist_dir=str(persist_dir),
        vector_store=vector_store
    )
    try:
        _index = load_index_from_storage(storage_context=storage_context)
    except Exception:
        _index = VectorStoreIndex.from_documents([], storage_context=storage_context)
    return _index

def _get_cross_encoder() -> Optional["CrossEncoder"]:
    global _cross_encoder
    if _cross_encoder is None and CrossEncoder is not None and settings.rerank_model:
        try:
            _cross_encoder = CrossEncoder(settings.rerank_model)
        except Exception:
            _cross_encoder = None
    return _cross_encoder

class SimpleEngine:
    def __init__(self):
        self.index = _load_or_create_index()

    def search(self, req: SearchRequest) -> List[SearchHit]:
        retriever = self.index.as_retriever(similarity_top_k=max(req.top_k * 4, 16))
        nodes = retriever.retrieve(req.query)

        # Optional rerank bằng cross-encoder
        if req.use_rerank and _get_cross_encoder() is not None and len(nodes) > 0:
            ce = _get_cross_encoder()
            pairs = [(req.query, n.get_text()) for n in nodes]
            scores = ce.predict(pairs)
            for n, s in zip(nodes, scores):
                n.score = float(s)
            nodes = sorted(nodes, key=lambda x: x.score, reverse=True)

        top_nodes = nodes[: req.top_k]
        hits: List[SearchHit] = []
        for n in top_nodes:
            meta = n.metadata or {}
            source_meta = SourceMeta(
                doc_id=str(meta.get("file_name") or meta.get("doc_id") or "unknown"),
                chunk_id=str(meta.get("id") or meta.get("chunk_id") or ""),
                page=meta.get("page"),
                extra={k: v for k, v in meta.items() if k not in ["file_name", "doc_id", "id", "chunk_id", "page"]},
            )
            hits.append(
                SearchHit(
                    text=n.get_text(),
                    score=float(n.score or 0.0),
                    meta=source_meta,
                    citation=CitationSpan(doc_id=source_meta.doc_id, page=source_meta.page, span=None),
                    rerank_score=float(n.score or 0.0) if req.use_rerank else None,
                )
            )
        return hits

_engine = None
def get_query_engine() -> SimpleEngine:
    global _engine
    if _engine is None:
        _engine = SimpleEngine()
    return _engine
