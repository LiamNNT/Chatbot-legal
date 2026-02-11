import logging
import os
from typing import Optional

from .ports.agent_port import AgentPort
from .ports.conversation_port import ConversationManagerPort
from .ports.embedding_port import EmbeddingPort
from .ports.fusion_port import FusionPort
from .ports.keyword_store_port import KeywordStorePort
from .ports.rag_port import RAGServicePort
from .ports.reranker_port import RerankerPort
from .ports.vector_store_port import VectorStorePort
from .use_cases.context_use_case import ContextUseCase
from .use_cases.conversation_use_case import ConversationUseCase
from .use_cases.prepare_request_use_case import PrepareAgentRequestUseCase
from .use_cases.search_use_case import SearchUseCase

logger = logging.getLogger(__name__)


class Container:
    def __init__(
        self,
        agent_port: Optional[AgentPort] = None,
        conversation_port: Optional[ConversationManagerPort] = None,
        rag_port: Optional[RAGServicePort] = None,
        vector_store: Optional[VectorStorePort] = None,
        keyword_store: Optional[KeywordStorePort] = None,
        embedding_port: Optional[EmbeddingPort] = None,
        reranker_port: Optional[RerankerPort] = None,
        fusion_port: Optional[FusionPort] = None,
        openrouter_api_key: Optional[str] = None,
        openrouter_model: str = "google/gemma-3-27b-it:free",
        use_redis: bool = False,
        redis_url: Optional[str] = None,
        max_messages: int = 20,
        max_history: int = 10,
        default_history_limit: int = 6,
        embedding_model: str = "intfloat/multilingual-e5-base",
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        weaviate_url: str = "http://localhost:8090",
        weaviate_collection: str = "VietnameseDocumentV3",
        opensearch_host: str = "localhost",
        opensearch_port: int = 9200,
        rrf_constant: int = 60,
        enable_reranker: bool = True,
    ):
        # ── 1. Low-level RAG Infrastructure ──
        self._embedding_port = embedding_port or self._create_embedding(embedding_model)
        self._vector_store = vector_store or self._create_vector_store(
            weaviate_url, weaviate_collection, self._embedding_port
        )
        self._keyword_store = keyword_store or self._create_keyword_store(
            opensearch_host, opensearch_port
        )
        self._reranker_port = reranker_port or self._create_reranker(
            reranker_model, enable_reranker
        )
        self._fusion_port = fusion_port or self._create_fusion(rrf_constant)

        # ── 2. SearchUseCase (replaces HTTP RAG service) ──
        self._search_use_case = SearchUseCase(
            vector_store=self._vector_store,
            keyword_store=self._keyword_store,
            reranker=self._reranker_port,
            fusion=self._fusion_port,
        )

        # ── 3. Core Infrastructure ──
        self._agent_port = agent_port or self._create_agent_port(
            openrouter_api_key, openrouter_model
        )
        self._conversation_port = conversation_port or self._create_conversation_port(
            use_redis, redis_url
        )
        self._rag_port = rag_port or self._create_rag_port(self._search_use_case)

        # ── 4. Use Cases ──
        self._conversation_use_case = ConversationUseCase(
            conversation_port=self._conversation_port,
            max_messages=max_messages,
            default_history_limit=default_history_limit,
        )
        self._context_use_case = ContextUseCase(agent_port=self._agent_port)
        self._prepare_request_use_case = PrepareAgentRequestUseCase(
            max_history=max_history,
            default_model=openrouter_model,
        )

        logger.info("DI Container initialized (all RAG in-process)")

    # ── Public accessors ─────────────────────────

    @property
    def agent_port(self) -> AgentPort:
        return self._agent_port

    @property
    def conversation_port(self) -> ConversationManagerPort:
        return self._conversation_port

    @property
    def rag_port(self) -> RAGServicePort:
        return self._rag_port

    @property
    def search_use_case(self) -> SearchUseCase:
        return self._search_use_case

    @property
    def conversation_use_case(self) -> ConversationUseCase:
        return self._conversation_use_case

    @property
    def context_use_case(self) -> ContextUseCase:
        return self._context_use_case

    @property
    def prepare_request_use_case(self) -> PrepareAgentRequestUseCase:
        return self._prepare_request_use_case

    @property
    def embedding_port(self) -> EmbeddingPort:
        return self._embedding_port

    @property
    def vector_store(self) -> VectorStorePort:
        return self._vector_store

    @property
    def keyword_store(self) -> Optional[KeywordStorePort]:
        return self._keyword_store

    @property
    def reranker_port(self) -> RerankerPort:
        return self._reranker_port

    @property
    def fusion_port(self) -> FusionPort:
        return self._fusion_port

    # ── Cleanup ──────────────────────────────────

    async def shutdown(self) -> None:
        """Release all adapter resources."""
        await self._agent_port.close()
        await self._rag_port.close()
        logger.info("Container shut down")

    # ── Factory helpers (private) ────────────────

    @staticmethod
    def _create_agent_port(api_key: Optional[str], model: str) -> AgentPort:
        from .infrastructure.openrouter_adapter import OpenRouterAdapter

        key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        if not key:
            logger.warning("OPENROUTER_API_KEY not set — LLM calls will fail")
        return OpenRouterAdapter(api_key=key, default_model=model)

    @staticmethod
    def _create_conversation_port(
        use_redis: bool, redis_url: Optional[str]
    ) -> ConversationManagerPort:
        from .infrastructure.conversation_manager import InMemoryConversationManager

        return InMemoryConversationManager(use_redis=use_redis, redis_url=redis_url)

    @staticmethod
    def _create_rag_port(search_uc: SearchUseCase) -> RAGServicePort:
        from .infrastructure.rag_adapter import LocalRAGAdapter

        return LocalRAGAdapter(search_use_case=search_uc)

    @staticmethod
    def _create_embedding(model_name: str) -> EmbeddingPort:
        from .infrastructure.rag.embedding_adapter import SentenceTransformerEmbedding

        return SentenceTransformerEmbedding(model_name=model_name)

    @staticmethod
    def _create_vector_store(
        url: str, collection: str, embedding: EmbeddingPort
    ) -> VectorStorePort:
        from .infrastructure.rag.weaviate_adapter import WeaviateVectorAdapter

        return WeaviateVectorAdapter(
            url=url, collection_name=collection, embedding_port=embedding
        )

    @staticmethod
    def _create_keyword_store(
        host: str, port: int
    ) -> Optional[KeywordStorePort]:
        try:
            from opensearchpy import OpenSearch

            client = OpenSearch(
                hosts=[{"host": host, "port": port}],
                use_ssl=False,
                verify_certs=False,
            )
            from .infrastructure.rag.opensearch_adapter import OpenSearchKeywordAdapter

            return OpenSearchKeywordAdapter(opensearch_client=client)
        except Exception as exc:
            logger.warning("OpenSearch unavailable (%s) — BM25 disabled", exc)
            return None

    @staticmethod
    def _create_reranker(model_name: str, enabled: bool) -> RerankerPort:
        if not enabled:
            from .infrastructure.rag.reranker_adapter import NoOpReranker
            return NoOpReranker()

        try:
            from .infrastructure.rag.reranker_adapter import CrossEncoderReranker
            return CrossEncoderReranker(model_name=model_name)
        except Exception as exc:
            logger.warning("CrossEncoder unavailable (%s) — using NoOp", exc)
            from .infrastructure.rag.reranker_adapter import NoOpReranker
            return NoOpReranker()

    @staticmethod
    def _create_fusion(rrf_constant: int) -> FusionPort:
        from .infrastructure.rag.fusion_adapter import RRFFusionService

        return RRFFusionService(rrf_constant=rrf_constant)
