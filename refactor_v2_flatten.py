#!/usr/bin/env python3
"""
Refactor V2: Flatten features + extract infrastructure + merge chat agents/reasoning.

Three goals:
1. Extract adapters/, store/, llm/ → infrastructure/ (sibling of app/)
2. Flatten feature folders (no sub-directories, only .py files)
3. Merge agents, langgraph, reasoning into chat/

Usage:
    python refactor_v2_flatten.py --dry-run    # Preview changes
    python refactor_v2_flatten.py --apply      # Execute changes
"""

import os
import re
import shutil
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent
ORCH = ROOT / "services" / "orchestrator"
RAG  = ROOT / "services" / "rag_services"

# ──────────────────────────────────────────────────────────────────────
# FILE MOVE MAPPINGS   (old_relative_path → new_relative_path)
# Paths are relative to the service root (ORCH or RAG)
# ──────────────────────────────────────────────────────────────────────

ORCH_MOVES: Dict[str, str] = {
    # ── 1. Adapters → infrastructure/ ─────────────────────────────
    "app/chat/adapters/openrouter_adapter.py": "infrastructure/openrouter_adapter.py",
    "app/chat/adapters/rag_adapter.py":        "infrastructure/rag_adapter.py",

    # ── 2. Flatten chat/agents/ → chat/ (rename base→agent_base) ─
    "app/chat/agents/base.py":                    "app/chat/agent_base.py",
    "app/chat/agents/answer_agent.py":            "app/chat/answer_agent.py",
    "app/chat/agents/smart_planner_agent.py":     "app/chat/smart_planner_agent.py",
    "app/chat/agents/response_formatter_agent.py":"app/chat/response_formatter_agent.py",
    "app/chat/agents/optimized_orchestrator.py":  "app/chat/optimized_orchestrator.py",

    # ── 3. Flatten chat/langgraph/ → chat/ (prefix langgraph_) ───
    "app/chat/langgraph/state.py":    "app/chat/langgraph_state.py",
    "app/chat/langgraph/nodes.py":    "app/chat/langgraph_nodes.py",
    "app/chat/langgraph/workflow.py": "app/chat/langgraph_workflow.py",

    # ── 4. Flatten chat/services/ → chat/ ────────────────────────
    "app/chat/services/orchestration_service.py": "app/chat/use_cases.py",
    "app/chat/services/context_service.py":       "app/chat/context_service.py",
    "app/chat/services/ircot_service.py":         "app/chat/ircot_service.py",
    "app/chat/services/planner_service.py":       "app/chat/planner_service.py",

    # ── 5. Merge reasoning/ → chat/ ─────────────────────────────
    "app/reasoning/graph_reasoning_agent.py":     "app/chat/graph_reasoning_agent.py",
    "app/reasoning/symbolic_reasoning_agent.py":  "app/chat/symbolic_reasoning_agent.py",
    "app/reasoning/symbolic_engine.py":           "app/chat/symbolic_engine.py",
    "app/reasoning/symbolic_graph_extension.py":  "app/chat/symbolic_graph_extension.py",
    "app/reasoning/context_enricher.py":          "app/chat/context_enricher.py",
    "app/reasoning/query_analyzer.py":            "app/chat/query_analyzer.py",
    "app/reasoning/reasoning_rules.py":           "app/chat/reasoning_rules.py",

    # ── 6. Flatten shared/config/ → shared/ ──────────────────────
    "app/shared/config/config_manager.py": "app/shared/config_manager.py",
    "app/shared/config/ircot_config.py":   "app/shared/ircot_config.py",

    # ── 7. Flatten shared/container/ → shared/ ───────────────────
    "app/shared/container/container.py":               "app/shared/container.py",
    "app/shared/container/container_legacy.py":        "app/shared/container_legacy.py",
    "app/shared/container/agent_factory.py":           "app/shared/agent_factory.py",
    "app/shared/container/graph_providers.py":         "app/shared/graph_providers.py",
    "app/shared/container/orchestration_providers.py": "app/shared/orchestration_providers.py",
    "app/shared/container/port_providers.py":          "app/shared/port_providers.py",

    # ── 8. Rename conversation/conversation_manager → use_cases ──
    "app/conversation/conversation_manager.py": "app/conversation/use_cases.py",
}

RAG_MOVES: Dict[str, str] = {
    # ── 1. search/adapters/ → infrastructure/ ────────────────────
    "app/search/adapters/cross_encoder_reranker.py":  "infrastructure/cross_encoder_reranker.py",
    "app/search/adapters/integration_adapter.py":     "infrastructure/search_integration_adapter.py",
    "app/search/adapters/llamaindex_vector_adapter.py":"infrastructure/llamaindex_vector_adapter.py",
    "app/search/adapters/weaviate_vector_adapter.py": "infrastructure/weaviate_vector_adapter.py",
    "app/search/adapters/opensearch_keyword_adapter.py":"infrastructure/opensearch_keyword_adapter.py",
    "app/search/adapters/service_adapters.py":        "infrastructure/search_service_adapters.py",
    # search/adapters/llamaindex/
    "app/search/adapters/llamaindex/hybrid_retriever.py": "infrastructure/llamaindex_hybrid_retriever.py",
    "app/search/adapters/llamaindex/postprocessors.py":   "infrastructure/llamaindex_postprocessors.py",
    "app/search/adapters/llamaindex/retriever.py":        "infrastructure/llamaindex_retriever.py",
    "app/search/adapters/llamaindex/search_service.py":   "infrastructure/llamaindex_search_service.py",
    # search/adapters/mappers/
    "app/search/adapters/mappers/llamaindex_mapper.py": "infrastructure/llamaindex_mapper.py",
    "app/search/adapters/mappers/search_mappers.py":    "infrastructure/search_mappers.py",

    # ── 2. knowledge_graph/adapters/ → infrastructure/ ───────────
    "app/knowledge_graph/adapters/neo4j_adapter.py": "infrastructure/neo4j_adapter.py",

    # ── 3. ingest/store/ → infrastructure/ ───────────────────────
    "app/ingest/store/opensearch/client.py":      "infrastructure/opensearch_client.py",
    "app/ingest/store/vector/chroma_store.py":    "infrastructure/chroma_store.py",
    "app/ingest/store/vector/faiss_store.py":     "infrastructure/faiss_store.py",
    "app/ingest/store/vector/weaviate_store.py":  "infrastructure/weaviate_store.py",

    # ── 4. llm/ → infrastructure/ ────────────────────────────────
    "app/llm/gemini_client.py":    "infrastructure/gemini_client.py",
    "app/llm/llm_client.py":      "infrastructure/llm_client.py",
    "app/llm/openai_client.py":   "infrastructure/openai_client.py",
    "app/llm/openrouter_client.py":"infrastructure/openrouter_client.py",

    # ── 5. Flatten search/ ───────────────────────────────────────
    "app/search/ports/repositories.py":  "app/search/ports.py",
    # services.py from ports/ needs merging with ports.py — handle via content append
    "app/search/services/search_service.py": "app/search/search_service.py",
    "app/search/services/api_facade.py":     "app/search/api_facade.py",
    # retrieval/ → flat in search/
    "app/search/retrieval/schemas.py":                "app/search/retrieval_schemas_models.py",
    "app/search/retrieval/legal_query_parser.py":     "app/search/legal_query_parser.py",
    "app/search/retrieval/metadata_filter_builder.py":"app/search/metadata_filter_builder.py",
    "app/search/retrieval/neighbor_expander.py":      "app/search/neighbor_expander.py",
    "app/search/retrieval/unified_retriever.py":      "app/search/unified_retriever.py",

    # ── 6. Flatten ingest/ ───────────────────────────────────────
    "app/ingest/indexing/graph_builder.py":          "app/ingest/graph_builder.py",
    "app/ingest/indexing/index_opensearch_data.py":  "app/ingest/index_opensearch_data.py",
    "app/ingest/indexing/index_semantic_data.py":    "app/ingest/index_semantic_data.py",
    "app/ingest/indexing/sync_entity_nodes.py":      "app/ingest/sync_entity_nodes.py",
    "app/ingest/loaders/llamaindex_legal_parser.py": "app/ingest/llamaindex_legal_parser.py",
    "app/ingest/loaders/vietnam_legal_docx_parser.py":"app/ingest/vietnam_legal_docx_parser.py",
    "app/ingest/services/ingest_service.py":         "app/ingest/use_cases.py",
    "app/ingest/services/job_store.py":              "app/ingest/job_store.py",
    "app/ingest/services/legal_ingestion_service.py":"app/ingest/legal_ingestion_service.py",
    "app/ingest/services/query_optimizer.py":        "app/ingest/query_optimizer.py",

    # ── 7. Flatten knowledge_graph/ ──────────────────────────────
    "app/knowledge_graph/domain/fusion_service.py":    "app/knowledge_graph/fusion_service.py",
    "app/knowledge_graph/domain/graph_models.py":      "app/knowledge_graph/graph_models.py",
    "app/knowledge_graph/domain/models.py":            "app/knowledge_graph/models.py",
    "app/knowledge_graph/domain/schema_mapper.py":     "app/knowledge_graph/schema_mapper.py",
    "app/knowledge_graph/domain/llamaindex_postprocessors.py": "app/knowledge_graph/llamaindex_postprocessors.py",
    "app/knowledge_graph/domain/llamaindex_retriever.py":      "app/knowledge_graph/llamaindex_retriever.py",
    "app/knowledge_graph/domain/llamaindex_search_service.py": "app/knowledge_graph/llamaindex_search_service.py",
    "app/knowledge_graph/ports/graph_repository.py":           "app/knowledge_graph/ports.py",
    "app/knowledge_graph/services/graph_builder_service.py":   "app/knowledge_graph/use_cases.py",
    "app/knowledge_graph/services/graph_builder_config.py":    "app/knowledge_graph/graph_builder_config.py",

    # ── 8. Flatten extraction/pipeline/ → extraction/ ────────────
    "app/extraction/pipeline/cleaner.py":              "app/extraction/cleaner.py",
    "app/extraction/pipeline/llamaindex_extractor.py": "app/extraction/llamaindex_extractor.py",
    "app/extraction/pipeline/page_merger.py":          "app/extraction/page_merger.py",
    "app/extraction/pipeline/post_processor.py":       "app/extraction/post_processor.py",
    "app/extraction/pipeline/schemas.py":              "app/extraction/schemas.py",
}

# ──────────────────────────────────────────────────────────────────────
# IMPORT REWRITE RULES
# Each rule:  (old_import_prefix, new_import_prefix)
# Applied as string replacement inside Python files.
# Order matters — more specific rules first.
# ──────────────────────────────────────────────────────────────────────

ORCH_IMPORT_RULES: List[Tuple[str, str]] = [
    # ── Adapters → infrastructure ─────────────────────────────────
    # From any depth, these references move to infrastructure package
    ("from ...chat.adapters.openrouter_adapter", "from infrastructure.openrouter_adapter"),
    ("from ...chat.adapters.rag_adapter",        "from infrastructure.rag_adapter"),
    ("from ..chat.adapters.openrouter_adapter",  "from infrastructure.openrouter_adapter"),
    ("from ..chat.adapters.rag_adapter",         "from infrastructure.rag_adapter"),

    # ── Flatten chat/agents/ → chat/ ─────────────────────────────
    # From inside chat (relative .agents.X → .X, base→agent_base)
    ("from .agents.base import",                "from .agent_base import"),
    ("from .agents.answer_agent import",        "from .answer_agent import"),
    ("from .agents.smart_planner_agent import", "from .smart_planner_agent import"),
    ("from .agents.response_formatter_agent import", "from .response_formatter_agent import"),
    ("from .agents.optimized_orchestrator import",   "from .optimized_orchestrator import"),
    ("from .agents import",                     "from . import"),
    # From outside chat (absolute-style relative)
    ("from ...chat.agents.base import",         "from ...chat.agent_base import"),
    ("from ...chat.agents.answer_agent import", "from ...chat.answer_agent import"),
    ("from ...chat.agents.smart_planner_agent import","from ...chat.smart_planner_agent import"),
    ("from ...chat.agents.response_formatter_agent import","from ...chat.response_formatter_agent import"),
    ("from ...chat.agents.optimized_orchestrator import","from ...chat.optimized_orchestrator import"),
    ("from ..chat.agents.base import",          "from ..chat.agent_base import"),
    ("from ..chat.agents.smart_planner_agent import","from ..chat.smart_planner_agent import"),

    # ── Flatten chat/langgraph/ → chat/ ──────────────────────────
    ("from .state import",  "from .langgraph_state import"),
    ("from .nodes import",  "from .langgraph_nodes import"),
    ("from ...chat.langgraph.workflow import", "from ...chat.langgraph_workflow import"),
    ("from ..langgraph.workflow import",       "from ..chat.langgraph_workflow import"),

    # ── Flatten chat/services/ → chat/ ───────────────────────────
    ("from ..services.ircot_service import",    "from .ircot_service import"),
    ("from ..services.context_service import",  "from .context_service import"),
    ("from .context_service import",            "from .context_service import"),  # already correct after move
    ("from ...chat.services.orchestration_service import", "from ...chat.use_cases import"),
    ("from ...chat.services.context_service import",       "from ...chat.context_service import"),

    # ── Merge reasoning/ → chat/ ─────────────────────────────────
    ("from ...reasoning.graph_reasoning_agent import",    "from ...chat.graph_reasoning_agent import"),
    ("from ...reasoning.symbolic_reasoning_agent import", "from ...chat.symbolic_reasoning_agent import"),
    ("from ...reasoning.symbolic_engine import",          "from ...chat.symbolic_engine import"),
    ("from ...reasoning.symbolic_graph_extension import", "from ...chat.symbolic_graph_extension import"),
    ("from ..reasoning.graph_reasoning_agent import",     "from ..chat.graph_reasoning_agent import"),
    ("from ..reasoning.symbolic_reasoning_agent import",  "from ..chat.symbolic_reasoning_agent import"),
    ("from ..reasoning.symbolic_engine import",           "from ..chat.symbolic_engine import"),
    ("from ..reasoning.symbolic_graph_extension import",  "from ..chat.symbolic_graph_extension import"),
    # Within reasoning/ files that reference siblings (now all in chat/)
    ("from .graph_reasoning_agent import",  "from .graph_reasoning_agent import"),  # same
    ("from .query_analyzer import",         "from .query_analyzer import"),         # same
    ("from .reasoning_rules import",        "from .reasoning_rules import"),        # same
    ("from .context_enricher import",       "from .context_enricher import"),       # same
    ("from ..reasoning import",             "from ..chat import"),

    # ── Flatten shared/config/ → shared/ ─────────────────────────
    ("from ..config.config_manager import",           "from .config_manager import"),
    ("from ..config.ircot_config import",             "from .ircot_config import"),
    ("from ...shared.config.config_manager import",   "from ...shared.config_manager import"),
    ("from ...shared.config.ircot_config import",     "from ...shared.ircot_config import"),
    ("from ..shared.config.ircot_config import",      "from ..shared.ircot_config import"),
    ("from ..shared.config.config_manager import",    "from ..shared.config_manager import"),

    # ── Flatten shared/container/ → shared/ ──────────────────────
    ("from ..shared.container.container import", "from ..shared.container import"),
    ("from ...shared.container.container import","from ...shared.container import"),
    ("from .port_providers import",   "from .port_providers import"),   # same level
    ("from .graph_providers import",  "from .graph_providers import"),  # same level
    ("from .orchestration_providers import", "from .orchestration_providers import"),
    ("from .agent_factory import",    "from .agent_factory import"),    # same level
    ("from ...shared.container import", "from ...shared.container import"),

    # ── Conversation rename ──────────────────────────────────────
    ("from ...conversation.conversation_manager import", "from ...conversation.use_cases import"),
    ("from ..conversation.conversation_manager import",  "from ..conversation.use_cases import"),

    # ── Backward-compat wrappers in app/agents/ ──────────────────
    ("from ..chat.agents.base import",                  "from ..chat.agent_base import"),
    ("from ..chat.agents.answer_agent import",          "from ..chat.answer_agent import"),
    ("from ..chat.agents.smart_planner_agent import",   "from ..chat.smart_planner_agent import"),
    ("from ..chat.agents.response_formatter_agent import","from ..chat.response_formatter_agent import"),
    ("from ..chat.agents.optimized_orchestrator import","from ..chat.optimized_orchestrator import"),
    ("from ..chat.agents import",                       "from ..chat import"),
    ("from ..reasoning.graph_reasoning_agent import",   "from ..chat.graph_reasoning_agent import"),
    ("from ..reasoning.symbolic_reasoning_agent import","from ..chat.symbolic_reasoning_agent import"),
    ("from ..reasoning import",                         "from ..chat import"),
]

RAG_IMPORT_RULES: List[Tuple[str, str]] = [
    # ── search/adapters/ → infrastructure ─────────────────────────
    ("from app.search.adapters.cross_encoder_reranker import",  "from infrastructure.cross_encoder_reranker import"),
    ("from app.search.adapters.integration_adapter import",     "from infrastructure.search_integration_adapter import"),
    ("from app.search.adapters.llamaindex_vector_adapter import","from infrastructure.llamaindex_vector_adapter import"),
    ("from app.search.adapters.weaviate_vector_adapter import", "from infrastructure.weaviate_vector_adapter import"),
    ("from app.search.adapters.opensearch_keyword_adapter import","from infrastructure.opensearch_keyword_adapter import"),
    ("from app.search.adapters.service_adapters import",        "from infrastructure.search_service_adapters import"),
    ("from app.search.adapters.llamaindex.hybrid_retriever import","from infrastructure.llamaindex_hybrid_retriever import"),
    ("from app.search.adapters.llamaindex.postprocessors import","from infrastructure.llamaindex_postprocessors import"),
    ("from app.search.adapters.llamaindex.retriever import",    "from infrastructure.llamaindex_retriever import"),
    ("from app.search.adapters.llamaindex.search_service import","from infrastructure.llamaindex_search_service import"),
    ("from app.search.adapters.mappers.llamaindex_mapper import","from infrastructure.llamaindex_mapper import"),
    ("from app.search.adapters.mappers.search_mappers import",  "from infrastructure.search_mappers import"),

    # ── knowledge_graph/adapters/ → infrastructure ────────────────
    ("from app.knowledge_graph.adapters.neo4j_adapter import", "from infrastructure.neo4j_adapter import"),
    ("from rag_services.app.knowledge_graph.adapters.neo4j_adapter import", "from infrastructure.neo4j_adapter import"),

    # ── ingest/store/ → infrastructure ────────────────────────────
    ("from app.ingest.store.opensearch.client import",    "from infrastructure.opensearch_client import"),
    ("from app.ingest.store.vector.chroma_store import",  "from infrastructure.chroma_store import"),
    ("from app.ingest.store.vector.faiss_store import",   "from infrastructure.faiss_store import"),
    ("from app.ingest.store.vector.weaviate_store import","from infrastructure.weaviate_store import"),

    # ── llm/ → infrastructure ─────────────────────────────────────
    ("from app.llm.gemini_client import",     "from infrastructure.gemini_client import"),
    ("from app.llm.llm_client import",        "from infrastructure.llm_client import"),
    ("from app.llm.openai_client import",     "from infrastructure.openai_client import"),
    ("from app.llm.openrouter_client import", "from infrastructure.openrouter_client import"),

    # ── Flatten search/ports/ → search/ports.py ──────────────────
    ("from app.search.ports.repositories import", "from app.search.ports import"),
    ("from app.search.ports.services import",     "from app.search.ports import"),

    # ── Flatten search/services/ → search/ ───────────────────────
    ("from app.search.services.search_service import", "from app.search.search_service import"),
    ("from app.search.services.api_facade import",     "from app.search.api_facade import"),

    # ── Flatten search/retrieval/ → search/ ──────────────────────
    ("from app.search.retrieval.schemas import",                "from app.search.retrieval_schemas_models import"),
    ("from app.search.retrieval.legal_query_parser import",     "from app.search.legal_query_parser import"),
    ("from app.search.retrieval.metadata_filter_builder import","from app.search.metadata_filter_builder import"),
    ("from app.search.retrieval.neighbor_expander import",      "from app.search.neighbor_expander import"),
    ("from app.search.retrieval.unified_retriever import",      "from app.search.unified_retriever import"),
    ("from app.search.retrieval import",                        "from app.search.retrieval_public import"),

    # ── Flatten ingest/ subdirs ───────────────────────────────────
    ("from app.ingest.indexing.graph_builder import",         "from app.ingest.graph_builder import"),
    ("from app.ingest.indexing.index_opensearch_data import", "from app.ingest.index_opensearch_data import"),
    ("from app.ingest.indexing.index_semantic_data import",   "from app.ingest.index_semantic_data import"),
    ("from app.ingest.indexing.sync_entity_nodes import",     "from app.ingest.sync_entity_nodes import"),
    ("from app.ingest.loaders.llamaindex_legal_parser import","from app.ingest.llamaindex_legal_parser import"),
    ("from app.ingest.loaders.vietnam_legal_docx_parser import","from app.ingest.vietnam_legal_docx_parser import"),
    ("from app.ingest.services.ingest_service import",        "from app.ingest.use_cases import"),
    ("from app.ingest.services.job_store import",             "from app.ingest.job_store import"),
    ("from app.ingest.services.legal_ingestion_service import","from app.ingest.legal_ingestion_service import"),
    ("from app.ingest.services.query_optimizer import",       "from app.ingest.query_optimizer import"),

    # ── Flatten knowledge_graph/ subdirs ──────────────────────────
    ("from app.knowledge_graph.domain.fusion_service import",    "from app.knowledge_graph.fusion_service import"),
    ("from app.knowledge_graph.domain.graph_models import",      "from app.knowledge_graph.graph_models import"),
    ("from app.knowledge_graph.domain.models import",            "from app.knowledge_graph.models import"),
    ("from app.knowledge_graph.domain.schema_mapper import",     "from app.knowledge_graph.schema_mapper import"),
    ("from app.knowledge_graph.domain.llamaindex_postprocessors import","from app.knowledge_graph.llamaindex_postprocessors import"),
    ("from app.knowledge_graph.domain.llamaindex_retriever import",    "from app.knowledge_graph.llamaindex_retriever import"),
    ("from app.knowledge_graph.domain.llamaindex_search_service import","from app.knowledge_graph.llamaindex_search_service import"),
    ("from app.knowledge_graph.ports.graph_repository import",         "from app.knowledge_graph.ports import"),
    ("from app.knowledge_graph.services.graph_builder_service import", "from app.knowledge_graph.use_cases import"),
    ("from app.knowledge_graph.services.graph_builder_config import",  "from app.knowledge_graph.graph_builder_config import"),

    # ── Flatten extraction/pipeline/ → extraction/ ────────────────
    ("from app.extraction.pipeline.cleaner import",              "from app.extraction.cleaner import"),
    ("from app.extraction.pipeline.llamaindex_extractor import", "from app.extraction.llamaindex_extractor import"),
    ("from app.extraction.pipeline.page_merger import",          "from app.extraction.page_merger import"),
    ("from app.extraction.pipeline.post_processor import",       "from app.extraction.post_processor import"),
    ("from app.extraction.pipeline.schemas import",              "from app.extraction.schemas import"),
    ("from app.extraction.page_merger import",                   "from app.extraction.page_merger import"),
    ("from app.extraction.schemas import",                       "from app.extraction.schemas import"),
]


def copy_file(src: Path, dst: Path, dry_run: bool):
    """Copy a file, creating parent dirs as needed."""
    if not src.exists():
        print(f"  ⚠  SKIP (not found): {src}")
        return False
    if dry_run:
        print(f"  📄 {src.relative_to(src.parents[2])}  →  {dst.relative_to(dst.parents[2])}")
        return True
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def rewrite_imports(filepath: Path, rules: List[Tuple[str, str]], dry_run: bool) -> int:
    """Rewrite import statements in a single file. Returns number of changes."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return 0
    original = content
    for old, new in rules:
        if old in content:
            content = content.replace(old, new)
    if content != original:
        if not dry_run:
            filepath.write_text(content, encoding="utf-8")
        return 1
    return 0


def merge_ports_files(svc_root: Path, dry_run: bool):
    """Merge search/ports/repositories.py + search/ports/services.py → search/ports.py"""
    repos = svc_root / "app" / "search" / "ports" / "repositories.py"
    svcs  = svc_root / "app" / "search" / "ports" / "services.py"
    dest  = svc_root / "app" / "search" / "ports.py"
    
    if not repos.exists() or not svcs.exists():
        return
    
    print(f"  🔀 Merging search/ports/ → search/ports.py")
    if dry_run:
        return
    
    repos_content = repos.read_text(encoding="utf-8")
    svcs_content = svcs.read_text(encoding="utf-8")
    
    merged = f'''"""
Search ports – repository & service interfaces.

Merged from ports/repositories.py and ports/services.py
"""

# ── Repository Interfaces ─────────────────────────────────────────
{repos_content}

# ── Service Interfaces ────────────────────────────────────────────
{svcs_content}
'''
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(merged, encoding="utf-8")


def create_retrieval_public(svc_root: Path, dry_run: bool):
    """Create search/retrieval_public.py as re-export shim for the old search/retrieval/__init__.py"""
    old_init = svc_root / "app" / "search" / "retrieval" / "__init__.py"
    dest = svc_root / "app" / "search" / "retrieval_public.py"
    
    if not old_init.exists():
        return
    
    print(f"  🔀 Creating search/retrieval_public.py from retrieval/__init__.py")
    if dry_run:
        return
    
    content = old_init.read_text(encoding="utf-8")
    # Rewrite its imports to flat structure
    content = content.replace("from app.search.retrieval.schemas import",
                               "from app.search.retrieval_schemas_models import")
    content = content.replace("from app.search.retrieval.legal_query_parser import",
                               "from app.search.legal_query_parser import")
    content = content.replace("from app.search.retrieval.metadata_filter_builder import",
                               "from app.search.metadata_filter_builder import")
    content = content.replace("from app.search.retrieval.neighbor_expander import",
                               "from app.search.neighbor_expander import")
    content = content.replace("from app.search.retrieval.unified_retriever import",
                               "from app.search.unified_retriever import")
    
    dest.write_text(content, encoding="utf-8")


def create_init_files(svc_root: Path, dry_run: bool):
    """Create __init__.py in new directories."""
    infra = svc_root / "infrastructure"
    if not dry_run:
        infra.mkdir(parents=True, exist_ok=True)
        init = infra / "__init__.py"
        if not init.exists():
            init.write_text('"""Infrastructure adapters, stores, and external clients."""\n')
    else:
        print(f"  📁 Create {infra / '__init__.py'}")


def cleanup_empty_dirs(svc_root: Path, dry_run: bool):
    """Remove now-empty subdirectories."""
    dirs_to_check = [
        "app/chat/adapters",
        "app/chat/agents",
        "app/chat/langgraph",
        "app/chat/services",
        "app/reasoning",
        "app/shared/config",
        "app/shared/container",
        # RAG-specific
        "app/search/adapters/llamaindex",
        "app/search/adapters/mappers",
        "app/search/adapters",
        "app/search/ports",
        "app/search/services",
        "app/search/retrieval",
        "app/ingest/indexing",
        "app/ingest/loaders",
        "app/ingest/services",
        "app/ingest/store/opensearch",
        "app/ingest/store/vector",
        "app/ingest/store",
        "app/knowledge_graph/adapters",
        "app/knowledge_graph/domain",
        "app/knowledge_graph/ports",
        "app/knowledge_graph/services",
        "app/extraction/pipeline",
        "app/llm",
    ]
    for d in dirs_to_check:
        dirpath = svc_root / d
        if dirpath.is_dir():
            # Check if only __init__.py or __pycache__ remain
            remaining = [f for f in dirpath.rglob("*") 
                        if f.is_file() and f.name != "__init__.py" 
                        and "__pycache__" not in str(f)]
            if not remaining:
                if dry_run:
                    print(f"  🗑  Remove empty dir: {d}/")
                else:
                    shutil.rmtree(dirpath, ignore_errors=True)


def update_orch_backward_compat(svc_root: Path, dry_run: bool):
    """Update backward-compat wrappers in app/agents/ and rewrite reasoning __init__."""
    agents_dir = svc_root / "app" / "agents"
    if not agents_dir.is_dir():
        return
    
    # The agents/__init__.py needs rewriting
    init_file = agents_dir / "__init__.py"
    if init_file.exists():
        new_content = '''"""Backward-compat – re-exports from app.chat (canonical location)."""
from ..chat import (  # noqa: F401
    SpecializedAgent, AgentConfig, AgentType,
    AnswerResult, DetailedSource,
)
from ..chat import SmartPlannerAgent, SmartPlanResult  # noqa: F401
from ..chat import AnswerAgent  # noqa: F401
from ..chat import ResponseFormatterAgent, FormattedResponseResult  # noqa: F401
from ..chat import OptimizedMultiAgentOrchestrator  # noqa: F401
from ..chat import (  # noqa: F401
    SymbolicReasoningEngine, ReasoningMode,
    SymbolicGraphExtension,
    GraphReasoningAgent, GraphQueryType, GraphReasoningResult,
    SymbolicReasoningAgent, SymbolicReasoningResult, SymbolicQueryType,
    QueryAnalyzer, QueryComponents,
    ContextEnricher,
)
'''
        if dry_run:
            print(f"  ✏️  Rewrite {init_file.relative_to(svc_root)}")
        else:
            init_file.write_text(new_content, encoding="utf-8")
    
    # Individual wrapper files
    wrappers = {
        "base.py": ('"""Backward-compat wrapper."""\n'
                     'from ..chat.agent_base import *  # noqa: F401,F403\n'
                     'from ..chat.agent_base import (\n'
                     '    AgentType, AgentConfig, SpecializedAgent,\n'
                     '    AnswerResult, DetailedSource,\n'
                     ')\n'),
        "optimized_orchestrator.py": ('"""Backward-compat wrapper."""\n'
                     'from ..chat.optimized_orchestrator import *  # noqa: F401,F403\n'
                     'from ..chat.optimized_orchestrator import OptimizedMultiAgentOrchestrator\n'),
        "answer_agent.py": ('"""Backward-compat wrapper."""\n'
                     'from ..chat.answer_agent import *  # noqa: F401,F403\n'
                     'from ..chat.answer_agent import AnswerAgent\n'),
        "smart_planner_agent.py": ('"""Backward-compat wrapper."""\n'
                     'from ..chat.smart_planner_agent import *  # noqa: F401,F403\n'
                     'from ..chat.smart_planner_agent import SmartPlannerAgent, SmartPlanResult, ExtractedFilters\n'),
        "response_formatter_agent.py": ('"""Backward-compat wrapper."""\n'
                     'from ..chat.response_formatter_agent import *  # noqa: F401,F403\n'
                     'from ..chat.response_formatter_agent import ResponseFormatterAgent, FormattedResponseResult\n'),
        "graph_reasoning_agent.py": ('"""Backward-compat wrapper."""\n'
                     'from ..chat.graph_reasoning_agent import *  # noqa: F401,F403\n'
                     'from ..chat.graph_reasoning_agent import GraphReasoningAgent, GraphQueryType, GraphReasoningResult\n'),
        "symbolic_reasoning_agent.py": ('"""Backward-compat wrapper."""\n'
                     'from ..chat.symbolic_reasoning_agent import *  # noqa: F401,F403\n'
                     'from ..chat.symbolic_reasoning_agent import SymbolicReasoningAgent, SymbolicReasoningResult, SymbolicQueryType\n'),
    }
    for fname, content in wrappers.items():
        fpath = agents_dir / fname
        if fpath.exists():
            if dry_run:
                print(f"  ✏️  Rewrite wrapper {fpath.relative_to(svc_root)}")
            else:
                fpath.write_text(content, encoding="utf-8")


def update_orch_chat_init(svc_root: Path, dry_run: bool):
    """Rewrite chat/__init__.py to export from flat structure."""
    init = svc_root / "app" / "chat" / "__init__.py"
    content = '''"""Chat feature – agents, reasoning, orchestration, LangGraph."""
from .agent_base import (  # noqa: F401
    SpecializedAgent, AgentConfig, AgentType,
    AnswerResult, DetailedSource,
)
from .smart_planner_agent import SmartPlannerAgent, SmartPlanResult  # noqa: F401
from .answer_agent import AnswerAgent  # noqa: F401
from .response_formatter_agent import ResponseFormatterAgent, FormattedResponseResult  # noqa: F401
from .optimized_orchestrator import OptimizedMultiAgentOrchestrator  # noqa: F401
from .graph_reasoning_agent import GraphReasoningAgent, GraphQueryType, GraphReasoningResult  # noqa: F401
from .symbolic_reasoning_agent import SymbolicReasoningAgent, SymbolicReasoningResult, SymbolicQueryType  # noqa: F401
from .symbolic_engine import SymbolicReasoningEngine, ReasoningMode  # noqa: F401
from .symbolic_graph_extension import SymbolicGraphExtension  # noqa: F401
from .query_analyzer import QueryAnalyzer, QueryComponents  # noqa: F401
from .context_enricher import ContextEnricher  # noqa: F401
'''
    if dry_run:
        print(f"  ✏️  Rewrite chat/__init__.py")
    else:
        init.write_text(content, encoding="utf-8")


def update_shared_init(svc_root: Path, dry_run: bool):
    """Rewrite shared/__init__.py for flattened layout."""
    init = svc_root / "app" / "shared" / "__init__.py"
    content = '''"""Shared cross-cutting concerns: domain, ports, container, config."""
from .container import get_container, cleanup_container, ServiceContainer  # noqa: F401
'''
    if dry_run:
        print(f"  ✏️  Rewrite shared/__init__.py")
    else:
        init.write_text(content, encoding="utf-8")


def run_orchestrator(dry_run: bool):
    print("\n" + "=" * 70)
    print("  ORCHESTRATOR REFACTORING")
    print("=" * 70)
    
    print("\n── Step 1: Create infrastructure/ ──")
    create_init_files(ORCH, dry_run)
    
    print("\n── Step 2: Copy files to new locations ──")
    moved = 0
    for old, new in ORCH_MOVES.items():
        src = ORCH / old
        dst = ORCH / new
        if copy_file(src, dst, dry_run):
            moved += 1
    print(f"  Total: {moved} files")
    
    print("\n── Step 3: Rewrite imports ──")
    changed = 0
    for pyfile in (ORCH / "app").rglob("*.py"):
        if "__pycache__" in str(pyfile):
            continue
        changed += rewrite_imports(pyfile, ORCH_IMPORT_RULES, dry_run)
    # Also rewrite infrastructure/ files
    infra = ORCH / "infrastructure"
    if infra.exists():
        for pyfile in infra.rglob("*.py"):
            if "__pycache__" in str(pyfile):
                continue
            changed += rewrite_imports(pyfile, ORCH_IMPORT_RULES, dry_run)
    print(f"  Files with rewritten imports: {changed}")
    
    print("\n── Step 4: Update backward-compat wrappers ──")
    update_orch_backward_compat(ORCH, dry_run)
    
    print("\n── Step 5: Update __init__.py files ──")
    update_orch_chat_init(ORCH, dry_run)
    update_shared_init(ORCH, dry_run)
    
    print("\n── Step 6: Remove old files ──")
    if not dry_run:
        for old in ORCH_MOVES:
            f = ORCH / old
            if f.exists():
                f.unlink()
                
    print("\n── Step 7: Cleanup empty directories ──")
    cleanup_empty_dirs(ORCH, dry_run)


def run_rag(dry_run: bool):
    print("\n" + "=" * 70)
    print("  RAG SERVICES REFACTORING")
    print("=" * 70)
    
    print("\n── Step 1: Create infrastructure/ ──")
    create_init_files(RAG, dry_run)
    
    print("\n── Step 2: Merge search/ports/ ──")
    merge_ports_files(RAG, dry_run)
    
    print("\n── Step 3: Create retrieval_public.py ──")
    create_retrieval_public(RAG, dry_run)
    
    print("\n── Step 4: Copy files to new locations ──")
    moved = 0
    for old, new in RAG_MOVES.items():
        src = RAG / old
        dst = RAG / new
        if copy_file(src, dst, dry_run):
            moved += 1
    print(f"  Total: {moved} files")
    
    print("\n── Step 5: Rewrite imports ──")
    changed = 0
    for pyfile in (RAG / "app").rglob("*.py"):
        if "__pycache__" in str(pyfile):
            continue
        changed += rewrite_imports(pyfile, RAG_IMPORT_RULES, dry_run)
    infra = RAG / "infrastructure"
    if infra.exists():
        for pyfile in infra.rglob("*.py"):
            if "__pycache__" in str(pyfile):
                continue
            changed += rewrite_imports(pyfile, RAG_IMPORT_RULES, dry_run)
    print(f"  Files with rewritten imports: {changed}")
    
    print("\n── Step 6: Remove old files ──")
    if not dry_run:
        for old in RAG_MOVES:
            f = RAG / old
            if f.exists():
                f.unlink()
    
    print("\n── Step 7: Cleanup empty directories ──")
    cleanup_empty_dirs(RAG, dry_run)


def main():
    parser = argparse.ArgumentParser(description="Refactor V2: Flatten + Infrastructure")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying files")
    parser.add_argument("--apply", action="store_true", help="Apply changes")
    parser.add_argument("--service", choices=["orchestrator", "rag", "both"], default="both",
                       help="Which service to refactor")
    args = parser.parse_args()
    
    if not args.dry_run and not args.apply:
        print("Please specify --dry-run or --apply")
        return
    
    dry_run = args.dry_run
    
    if dry_run:
        print("🔍 DRY RUN MODE — no files will be modified\n")
    else:
        print("🚀 APPLYING CHANGES\n")
    
    if args.service in ("orchestrator", "both"):
        run_orchestrator(dry_run)
    
    if args.service in ("rag", "both"):
        run_rag(dry_run)
    
    print("\n" + "=" * 70)
    if dry_run:
        print("✅ Dry run complete. Use --apply to execute.")
    else:
        print("✅ Refactoring complete!")
        print("   Next: verify imports with `grep -rn 'from.*adapters\\|from.*store\\|from.*llm' app/`")
    print("=" * 70)


if __name__ == "__main__":
    main()
