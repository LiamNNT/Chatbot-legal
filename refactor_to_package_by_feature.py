#!/usr/bin/env python3
"""
Refactor Orchestrator & RAG Services to Package-by-Feature structure.

Usage:
    python refactor_to_package_by_feature.py            # dry-run (shows plan)
    python refactor_to_package_by_feature.py --apply     # actually moves files & updates imports

Rollback:
    git checkout -- services/orchestrator services/rag_services
"""

import os
import re
import sys
import shutil
import argparse
from pathlib import Path
from typing import List, Tuple, Dict

ROOT = Path(__file__).parent
ORCH = ROOT / "services" / "orchestrator"
RAG  = ROOT / "services" / "rag_services"

# ══════════════════════════════════════════════════════════════
#  ORCHESTRATOR MAPPING  (old relative → new relative, from app/)
# ══════════════════════════════════════════════════════════════
ORCH_MOVES: List[Tuple[str, str]] = [
    # ── shared/domain ──
    ("core/domain/domain.py",           "shared/domain.py"),
    ("core/domain/exceptions.py",       "shared/exceptions.py"),
    ("core/domain/__init__.py",         "shared/domain_pkg/__init__.py"),  # will be cleaned up

    # ── shared/ports ──
    ("ports/agent_ports.py",            "shared/ports.py"),
    ("ports/__init__.py",               None),  # delete marker

    # ── shared/schemas ──
    ("schemas/api_schemas.py",          "shared/schemas.py"),
    ("schemas/__init__.py",             None),

    # ── shared/config ──
    ("core/config/config_manager.py",   "shared/config/config_manager.py"),
    ("core/config/ircot_config.py",     "shared/config/ircot_config.py"),
    ("core/config/__init__.py",         "shared/config/__init__.py"),

    # ── shared/container (DI) ──
    ("core/DI/container.py",            "shared/container/container.py"),
    ("core/DI/port_providers.py",       "shared/container/port_providers.py"),
    ("core/DI/graph_providers.py",      "shared/container/graph_providers.py"),
    ("core/DI/orchestration_providers.py", "shared/container/orchestration_providers.py"),
    ("core/DI/agent_factory.py",        "shared/container/agent_factory.py"),
    ("core/DI/container_legacy.py",     "shared/container/container_legacy.py"),
    ("core/DI/__init__.py",             "shared/container/__init__.py"),

    # ── chat feature ──
    ("api/routes/chat_routes.py",       "chat/routes.py"),
    ("api/routes/response_mappers.py",  "chat/response_mappers.py"),
    ("api/exception_handlers.py",       "chat/exception_handlers.py"),

    # chat/services
    ("core/services/orchestration_service.py", "chat/services/orchestration_service.py"),
    ("core/services/ircot_service.py",         "chat/services/ircot_service.py"),
    ("core/services/context_domain_service.py", "chat/services/context_service.py"),
    ("core/services/planner_domain_service.py", "chat/services/planner_service.py"),

    # chat/agents
    ("core/agents/base.py",                     "chat/agents/base.py"),
    ("core/agents/answer_agent.py",             "chat/agents/answer_agent.py"),
    ("core/agents/smart_planner_agent.py",      "chat/agents/smart_planner_agent.py"),
    ("core/agents/response_formatter_agent.py", "chat/agents/response_formatter_agent.py"),
    ("core/agents/optimized_orchestrator.py",   "chat/agents/optimized_orchestrator.py"),
    ("core/agents/__init__.py",                 "chat/agents/__init__.py"),

    # chat/langgraph
    ("core/langgraph/langgraph_nodes.py",    "chat/langgraph/nodes.py"),
    ("core/langgraph/langgraph_state.py",    "chat/langgraph/state.py"),
    ("core/langgraph/langgraph_workflow.py", "chat/langgraph/workflow.py"),
    ("core/langgraph/__init__.py",           "chat/langgraph/__init__.py"),

    # chat/adapters
    ("adapters/openrouter_adapter.py", "chat/adapters/openrouter_adapter.py"),
    ("adapters/rag_adapter.py",        "chat/adapters/rag_adapter.py"),
    ("adapters/__init__.py",           None),

    # ── conversation feature ──
    ("api/routes/conversation_routes.py", "conversation/routes.py"),
    ("adapters/conversation_manager.py",  "conversation/conversation_manager.py"),

    # ── reasoning feature ──
    ("core/agents/graph_reasoning_agent.py",    "reasoning/graph_reasoning_agent.py"),
    ("core/agents/symbolic_reasoning_agent.py", "reasoning/symbolic_reasoning_agent.py"),
    ("core/reasoning/symbolic_engine.py",       "reasoning/symbolic_engine.py"),
    ("core/reasoning/reasoning_rules.py",       "reasoning/reasoning_rules.py"),
    ("core/reasoning/query_analyzer.py",        "reasoning/query_analyzer.py"),
    ("core/reasoning/context_enricher.py",      "reasoning/context_enricher.py"),
    ("core/reasoning/symbolic_graph_extension.py", "reasoning/symbolic_graph_extension.py"),
    ("core/reasoning/__init__.py",              "reasoning/__init__.py"),

    # ── admin feature ──
    ("api/routes/admin_routes.py", "admin/routes.py"),

    # ── old top-level packages to delete ──
    ("api/routes/__init__.py",      None),
    ("api/__init__.py",             None),
    ("core/services/__init__.py",   None),
    ("core/agents/__init__.py",     None),  # already moved
    ("core/__init__.py",            None),
]

# Import path rewrites for orchestrator (old → new)
# These are relative-import prefixes from inside app/
ORCH_IMPORT_REWRITES: List[Tuple[str, str]] = [
    # Domain & exceptions
    ("..core.domain.domain",          "..shared.domain"),
    (".core.domain.domain",           ".shared.domain"),
    ("...core.domain.domain",         "...shared.domain"),
    ("..core.domain.exceptions",      "..shared.exceptions"),
    (".core.domain.exceptions",       ".shared.exceptions"),
    ("...core.domain.exceptions",     "...shared.exceptions"),

    # Ports
    ("..ports.agent_ports",           "..shared.ports"),
    (".ports.agent_ports",            ".shared.ports"),
    ("...ports.agent_ports",          "...shared.ports"),

    # Schemas
    ("..schemas.api_schemas",         "..shared.schemas"),
    (".schemas.api_schemas",          ".shared.schemas"),
    ("...schemas.api_schemas",        "...shared.schemas"),

    # Config
    ("..core.config.",                "..shared.config."),
    (".core.config.",                 ".shared.config."),
    ("...core.config.",               "...shared.config."),
    ("..config.config_manager",       "..shared.config.config_manager"),
    ("..config.ircot_config",         "..shared.config.ircot_config"),

    # DI Container
    (".core.DI.container",            ".shared.container.container"),
    ("..core.DI.container",           "..shared.container.container"),
    ("...core.DI.container",          "...shared.container.container"),
    (".core.DI.",                      ".shared.container."),
    ("..core.DI.",                     "..shared.container."),
    ("...core.DI.",                    "...shared.container."),

    # Agents → chat/agents
    ("..core.agents.base",            "..chat.agents.base"),
    (".core.agents.base",             ".chat.agents.base"),
    ("..core.agents.",                "..chat.agents."),
    (".core.agents.",                 ".chat.agents."),
    ("...core.agents.",               "...chat.agents."),

    # Reasoning
    ("..core.reasoning.",             "..reasoning."),
    (".core.reasoning.",              ".reasoning."),
    ("..reasoning.symbolic_engine",   "..reasoning.symbolic_engine"),
    ("..reasoning.symbolic_graph_extension", "..reasoning.symbolic_graph_extension"),

    # Services → chat/services
    ("..core.services.",              "..chat.services."),
    (".core.services.",               ".chat.services."),
    ("...core.services.",             "...chat.services."),
    ("..services.orchestration_service", "..chat.services.orchestration_service"),
    ("..services.ircot_service",      "..chat.services.ircot_service"),
    ("..services.context_domain_service", "..chat.services.context_service"),
    ("..services.planner_domain_service", "..chat.services.planner_service"),

    # Adapters → chat/adapters
    ("..adapters.openrouter_adapter", "..chat.adapters.openrouter_adapter"),
    (".adapters.openrouter_adapter",  ".chat.adapters.openrouter_adapter"),
    ("...adapters.openrouter_adapter", "...chat.adapters.openrouter_adapter"),
    ("..adapters.rag_adapter",        "..chat.adapters.rag_adapter"),
    (".adapters.rag_adapter",         ".chat.adapters.rag_adapter"),
    ("...adapters.rag_adapter",       "...chat.adapters.rag_adapter"),
    ("..adapters.conversation_manager", "..conversation.conversation_manager"),
    (".adapters.conversation_manager",  ".conversation.conversation_manager"),
    ("...adapters.conversation_manager", "...conversation.conversation_manager"),

    # Routes
    (".api.routes",                   ".chat.routes"),
    ("..api.routes",                  "..chat.routes"),
    (".api.exception_handlers",       ".chat.exception_handlers"),
    ("..api.exception_handlers",      "..chat.exception_handlers"),

    # LangGraph
    ("..core.langgraph.",             "..chat.langgraph."),
    (".core.langgraph.",              ".chat.langgraph."),
    (".langgraph_state",              ".state"),
    (".langgraph_nodes",              ".nodes"),
    (".langgraph_workflow",           ".workflow"),

    # Graph reasoning agents → reasoning/
    ("..core.agents.graph_reasoning_agent", "..reasoning.graph_reasoning_agent"),
    (".graph_reasoning_agent",        ".graph_reasoning_agent"),  # local imports within reasoning/
    ("..core.agents.symbolic_reasoning_agent", "..reasoning.symbolic_reasoning_agent"),
]


# ══════════════════════════════════════════════════════════════
#  RAG SERVICES MAPPING  (old relative → new relative, from rag_services/)
# ══════════════════════════════════════════════════════════════
RAG_MOVES: List[Tuple[str, str]] = [
    # ── shared ──
    ("app/config/settings.py",      "app/shared/config/settings.py"),
    ("app/config/logging.py",       "app/shared/config/logging.py"),
    ("app/config/__init__.py",      "app/shared/config/__init__.py"),
    ("app/api/schemas/common.py",   "app/shared/schemas/common.py"),
    ("app/api/schemas/doc.py",      "app/shared/schemas/doc.py"),
    ("app/core/utils/json_utils.py","app/shared/utils/json_utils.py"),
    ("app/core/utils/__init__.py",  "app/shared/utils/__init__.py"),
    ("infrastructure/container.py", "app/shared/container/container.py"),
    ("infrastructure/ingest_factory.py","app/shared/container/ingest_factory.py"),
    ("infrastructure/__init__.py",  None),

    # ── search feature ──
    ("app/api/v1/routes/search.py",         "app/search/routes.py"),
    ("app/api/schemas/search.py",           "app/search/schemas.py"),
    ("app/api/v1/routes/retrieval.py",      "app/search/retrieval_routes.py"),
    ("app/api/schemas/retrieval.py",        "app/search/retrieval_schemas.py"),
    ("core/domain/search_service.py",       "app/search/services/search_service.py"),
    ("adapters/api_facade.py",              "app/search/services/api_facade.py"),

    # search/retrieval
    ("app/core/retrieval/legal_query_parser.py",     "app/search/retrieval/legal_query_parser.py"),
    ("app/core/retrieval/metadata_filter_builder.py","app/search/retrieval/metadata_filter_builder.py"),
    ("app/core/retrieval/neighbor_expander.py",      "app/search/retrieval/neighbor_expander.py"),
    ("app/core/retrieval/schemas.py",                "app/search/retrieval/schemas.py"),
    ("app/core/retrieval/unified_retriever.py",      "app/search/retrieval/unified_retriever.py"),
    ("app/core/retrieval/__init__.py",               "app/search/retrieval/__init__.py"),

    # search/adapters
    ("adapters/weaviate_vector_adapter.py",     "app/search/adapters/weaviate_vector_adapter.py"),
    ("adapters/llamaindex_vector_adapter.py",   "app/search/adapters/llamaindex_vector_adapter.py"),
    ("adapters/opensearch_keyword_adapter.py",  "app/search/adapters/opensearch_keyword_adapter.py"),
    ("adapters/cross_encoder_reranker.py",      "app/search/adapters/cross_encoder_reranker.py"),
    ("adapters/service_adapters.py",            "app/search/adapters/service_adapters.py"),
    ("adapters/integration_adapter.py",         "app/search/adapters/integration_adapter.py"),

    # search/adapters/llamaindex
    ("adapters/llamaindex/__init__.py",         "app/search/adapters/llamaindex/__init__.py"),
    ("adapters/llamaindex/hybrid_retriever.py", "app/search/adapters/llamaindex/hybrid_retriever.py"),
    ("adapters/llamaindex/postprocessors.py",   "app/search/adapters/llamaindex/postprocessors.py"),
    ("adapters/llamaindex/retriever.py",        "app/search/adapters/llamaindex/retriever.py"),
    ("adapters/llamaindex/search_service.py",   "app/search/adapters/llamaindex/search_service.py"),

    # search/adapters/mappers
    ("adapters/mappers/__init__.py",            "app/search/adapters/mappers/__init__.py"),
    ("adapters/mappers/llamaindex_mapper.py",   "app/search/adapters/mappers/llamaindex_mapper.py"),
    ("adapters/mappers/search_mappers.py",      "app/search/adapters/mappers/search_mappers.py"),

    # search/ports
    ("core/ports/repositories.py",  "app/search/ports/repositories.py"),
    ("core/ports/services.py",      "app/search/ports/services.py"),

    # ── ingest feature ──
    ("app/api/v1/routes/ingest.py",     "app/ingest/routes.py"),
    ("app/api/schemas/ingest.py",       "app/ingest/schemas.py"),
    ("app/api/v1/routes/opensearch.py", "app/ingest/opensearch_routes.py"),

    # ingest/services
    ("core/services/ingest_service.py",         "app/ingest/services/ingest_service.py"),
    ("core/services/legal_ingestion_service.py","app/ingest/services/legal_ingestion_service.py"),
    ("core/services/job_store.py",              "app/ingest/services/job_store.py"),
    ("core/services/query_optimizer.py",        "app/ingest/services/query_optimizer.py"),

    # ingest/indexing
    ("app/core/indexing/graph_builder.py",          "app/ingest/indexing/graph_builder.py"),
    ("app/core/indexing/index_opensearch_data.py",  "app/ingest/indexing/index_opensearch_data.py"),
    ("app/core/indexing/index_semantic_data.py",    "app/ingest/indexing/index_semantic_data.py"),
    ("app/core/indexing/sync_entity_nodes.py",      "app/ingest/indexing/sync_entity_nodes.py"),
    ("app/core/indexing/__init__.py",               "app/ingest/indexing/__init__.py"),

    # ingest/loaders
    ("indexing/loaders/__init__.py",                    "app/ingest/loaders/__init__.py"),
    ("indexing/loaders/llamaindex_legal_parser.py",     "app/ingest/loaders/llamaindex_legal_parser.py"),
    ("indexing/loaders/vietnam_legal_docx_parser.py",   "app/ingest/loaders/vietnam_legal_docx_parser.py"),

    # ingest/store
    ("infrastructure/store/__init__.py",            "app/ingest/store/__init__.py"),
    ("infrastructure/store/opensearch/__init__.py", "app/ingest/store/opensearch/__init__.py"),
    ("infrastructure/store/opensearch/client.py",   "app/ingest/store/opensearch/client.py"),
    ("infrastructure/store/vector/__init__.py",     "app/ingest/store/vector/__init__.py"),
    ("infrastructure/store/vector/chroma_store.py", "app/ingest/store/vector/chroma_store.py"),
    ("infrastructure/store/vector/faiss_store.py",  "app/ingest/store/vector/faiss_store.py"),
    ("infrastructure/store/vector/weaviate_store.py","app/ingest/store/vector/weaviate_store.py"),

    # ── extraction feature ──
    ("app/api/v1/routes/extraction.py",     "app/extraction/routes.py"),
    ("app/core/extraction/cleaner.py",      "app/extraction/pipeline/cleaner.py"),
    ("app/core/extraction/llamaindex_extractor.py", "app/extraction/pipeline/llamaindex_extractor.py"),
    ("app/core/extraction/page_merger.py",  "app/extraction/pipeline/page_merger.py"),
    ("app/core/extraction/post_processor.py","app/extraction/pipeline/post_processor.py"),
    ("app/core/extraction/schemas.py",      "app/extraction/pipeline/schemas.py"),
    ("app/core/extraction/__init__.py",     "app/extraction/__init__.py"),

    # ── knowledge_graph feature ──
    ("app/api/v1/routes/kg.py",             "app/knowledge_graph/routes.py"),
    ("core/domain/graph_models.py",         "app/knowledge_graph/domain/graph_models.py"),
    ("core/domain/fusion_service.py",       "app/knowledge_graph/domain/fusion_service.py"),
    ("core/domain/models.py",              "app/knowledge_graph/domain/models.py"),
    ("core/domain/schema_mapper.py",       "app/knowledge_graph/domain/schema_mapper.py"),
    ("core/domain/llamaindex_postprocessors.py", "app/knowledge_graph/domain/llamaindex_postprocessors.py"),
    ("core/domain/llamaindex_retriever.py", "app/knowledge_graph/domain/llamaindex_retriever.py"),
    ("core/domain/llamaindex_search_service.py", "app/knowledge_graph/domain/llamaindex_search_service.py"),
    ("core/services/graph_builder_service.py",  "app/knowledge_graph/services/graph_builder_service.py"),
    ("core/services/graph_builder_config.py",   "app/knowledge_graph/services/graph_builder_config.py"),
    ("adapters/graph/__init__.py",          "app/knowledge_graph/adapters/__init__.py"),
    ("adapters/graph/neo4j_adapter.py",     "app/knowledge_graph/adapters/neo4j_adapter.py"),
    ("core/ports/graph_repository.py",      "app/knowledge_graph/ports/graph_repository.py"),
    ("core/domain/__init__.py",             "app/knowledge_graph/domain/__init__.py"),
    ("core/ports/__init__.py",              "app/knowledge_graph/ports/__init__.py"),

    # ── embedding feature ──
    ("app/api/v1/routes/embed.py",  "app/embedding/routes.py"),
    ("app/api/schemas/embed.py",    "app/embedding/schemas.py"),

    # ── admin feature ──
    ("app/api/v1/routes/admin.py",  "app/admin/routes.py"),

    # ── health feature ──
    ("app/api/v1/routes/health.py",     "app/health/routes.py"),
    ("app/api/endpoints/health.py",     "app/health/health_v2.py"),

    # ── llm (shared adapter) ──
    ("adapters/llm/__init__.py",         "app/llm/__init__.py"),
    ("adapters/llm/gemini_client.py",    "app/llm/gemini_client.py"),
    ("adapters/llm/llm_client.py",       "app/llm/llm_client.py"),
    ("adapters/llm/openai_client.py",    "app/llm/openai_client.py"),
    ("adapters/llm/openrouter_client.py","app/llm/openrouter_client.py"),
]

RAG_IMPORT_REWRITES: List[Tuple[str, str]] = [
    # Config
    ("app.config.settings",         "app.shared.config.settings"),
    ("app.config.logging",          "app.shared.config.logging"),

    # Schemas (shared)
    ("app.api.schemas.common",      "app.shared.schemas.common"),
    ("app.api.schemas.doc",         "app.shared.schemas.doc"),
    ("app.api.schemas.search",      "app.search.schemas"),
    ("app.api.schemas.retrieval",   "app.search.retrieval_schemas"),
    ("app.api.schemas.ingest",      "app.ingest.schemas"),
    ("app.api.schemas.embed",       "app.embedding.schemas"),

    # Container
    ("infrastructure.container",    "app.shared.container.container"),
    ("infrastructure.ingest_factory","app.shared.container.ingest_factory"),
    ("core.container",              "app.shared.container.container"),

    # Utils
    ("app.core.utils.",             "app.shared.utils."),

    # Search / retrieval
    ("adapters.api_facade",         "app.search.services.api_facade"),
    ("core.domain.search_service",  "app.search.services.search_service"),
    ("app.core.retrieval",          "app.search.retrieval"),

    # Adapters → search/adapters
    ("adapters.weaviate_vector_adapter",    "app.search.adapters.weaviate_vector_adapter"),
    ("adapters.llamaindex_vector_adapter",  "app.search.adapters.llamaindex_vector_adapter"),
    ("adapters.opensearch_keyword_adapter", "app.search.adapters.opensearch_keyword_adapter"),
    ("adapters.cross_encoder_reranker",     "app.search.adapters.cross_encoder_reranker"),
    ("adapters.service_adapters",           "app.search.adapters.service_adapters"),
    ("adapters.integration_adapter",        "app.search.adapters.integration_adapter"),
    ("adapters.llamaindex.",                "app.search.adapters.llamaindex."),
    ("adapters.mappers.",                   "app.search.adapters.mappers."),

    # Ports
    ("core.ports.repositories",     "app.search.ports.repositories"),
    ("core.ports.services",         "app.search.ports.services"),
    ("core.ports.graph_repository", "app.knowledge_graph.ports.graph_repository"),

    # Ingest services
    ("core.services.ingest_service",          "app.ingest.services.ingest_service"),
    ("core.services.legal_ingestion_service", "app.ingest.services.legal_ingestion_service"),
    ("core.services.job_store",               "app.ingest.services.job_store"),
    ("core.services.query_optimizer",         "app.ingest.services.query_optimizer"),

    # KG services
    ("core.services.graph_builder_service",   "app.knowledge_graph.services.graph_builder_service"),
    ("core.services.graph_builder_config",    "app.knowledge_graph.services.graph_builder_config"),
    ("core.services.",                        "app.knowledge_graph.services."),

    # Domain (graph models)
    ("core.domain.graph_models",        "app.knowledge_graph.domain.graph_models"),
    ("core.domain.fusion_service",      "app.knowledge_graph.domain.fusion_service"),
    ("core.domain.models",              "app.knowledge_graph.domain.models"),
    ("core.domain.schema_mapper",       "app.knowledge_graph.domain.schema_mapper"),
    ("core.domain.llamaindex_postprocessors", "app.knowledge_graph.domain.llamaindex_postprocessors"),
    ("core.domain.llamaindex_retriever",      "app.knowledge_graph.domain.llamaindex_retriever"),
    ("core.domain.llamaindex_search_service", "app.knowledge_graph.domain.llamaindex_search_service"),
    ("core.domain.",                    "app.knowledge_graph.domain."),

    # Graph adapters
    ("adapters.graph.",                 "app.knowledge_graph.adapters."),

    # LLM adapters
    ("adapters.llm.",                   "app.llm."),

    # Extraction
    ("app.core.extraction",             "app.extraction"),
    ("app.core.indexing.",              "app.ingest.indexing."),

    # indexing loaders
    ("indexing.loaders.",               "app.ingest.loaders."),

    # Infrastructure store
    ("infrastructure.store.",           "app.ingest.store."),

    # Health endpoints
    ("app.api.endpoints.health",        "app.health.health_v2"),

    # Routes (for main.py)
    ("app.api.v1.routes.health",    "app.health.routes"),
    ("app.api.v1.routes.embed",     "app.embedding.routes"),
    ("app.api.v1.routes.search",    "app.search.routes"),
    ("app.api.v1.routes.admin",     "app.admin.routes"),
    ("app.api.v1.routes.opensearch","app.ingest.opensearch_routes"),
    ("app.api.v1.routes.extraction","app.extraction.routes"),
    ("app.api.v1.routes.ingest",    "app.ingest.routes"),
    ("app.api.v1.routes.retrieval", "app.search.retrieval_routes"),
    ("app.api.v1.routes.kg",        "app.knowledge_graph.routes"),
]


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════

def ensure_init(directory: Path):
    """Create __init__.py if it doesn't exist."""
    init = directory / "__init__.py"
    if not init.exists():
        init.write_text("")


def move_file(src: Path, dst: Path, dry_run: bool):
    """Move a file, creating parent dirs as needed."""
    if not src.exists():
        print(f"  ⚠  SKIP (not found): {src}")
        return False
    if dry_run:
        print(f"  📦 {src.relative_to(ROOT)}  →  {dst.relative_to(ROOT)}")
        return True
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  ✅ {src.relative_to(ROOT)}  →  {dst.relative_to(ROOT)}")
    return True


def rewrite_imports_in_file(filepath: Path, rewrites: List[Tuple[str, str]], dry_run: bool):
    """Apply import rewrites to a single file."""
    if not filepath.exists() or filepath.suffix != ".py":
        return 0

    text = filepath.read_text(encoding="utf-8")
    original = text
    changes = 0

    for old, new in rewrites:
        # Only rewrite in import/from lines
        pattern = re.compile(
            r'^(\s*(?:from|import)\s+.*)' + re.escape(old),
            re.MULTILINE
        )
        new_text = pattern.sub(lambda m: m.group(0).replace(old, new), text)
        if new_text != text:
            changes += text.count(old) - new_text.count(old) + new_text.count(new) - text.count(new)
            text = new_text

    if text != original:
        if dry_run:
            print(f"  📝 Would update imports in: {filepath.relative_to(ROOT)}")
        else:
            filepath.write_text(text, encoding="utf-8")
            print(f"  📝 Updated imports in: {filepath.relative_to(ROOT)}")
        return 1
    return 0


def create_init_files(base: Path, dry_run: bool):
    """Ensure all Python package dirs have __init__.py."""
    for dirpath, dirnames, filenames in os.walk(base):
        d = Path(dirpath)
        # Skip __pycache__ and hidden dirs
        if "__pycache__" in str(d) or any(p.startswith(".") for p in d.parts):
            continue
        # If the directory contains .py files (or subdirs that are packages), add __init__.py
        has_py = any(f.endswith(".py") for f in filenames)
        has_subpackage = any((d / sub / "__init__.py").exists() for sub in dirnames)
        if has_py or has_subpackage:
            init = d / "__init__.py"
            if not init.exists():
                if dry_run:
                    print(f"  📄 Would create: {init.relative_to(ROOT)}")
                else:
                    init.write_text("")
                    print(f"  📄 Created: {init.relative_to(ROOT)}")


def cleanup_empty_dirs(base: Path, dry_run: bool):
    """Remove empty directories (except __pycache__)."""
    for dirpath, dirnames, filenames in os.walk(base, topdown=False):
        d = Path(dirpath)
        if "__pycache__" in str(d):
            continue
        # Check if directory only has __pycache__ or is empty
        remaining = [f for f in os.listdir(d) if f != "__pycache__" and f != ".pyc"]
        if not remaining and d != base:
            if dry_run:
                print(f"  🗑️  Would remove empty dir: {d.relative_to(ROOT)}")
            else:
                shutil.rmtree(d, ignore_errors=True)
                print(f"  🗑️  Removed empty dir: {d.relative_to(ROOT)}")


def cleanup_pycache(base: Path, dry_run: bool):
    """Remove all __pycache__ directories."""
    for dirpath, dirnames, filenames in os.walk(base, topdown=False):
        d = Path(dirpath)
        if d.name == "__pycache__":
            if dry_run:
                print(f"  🗑️  Would remove: {d.relative_to(ROOT)}")
            else:
                shutil.rmtree(d, ignore_errors=True)
                print(f"  🗑️  Removed: {d.relative_to(ROOT)}")


# ══════════════════════════════════════════════════════════════
#  ORCHESTRATOR-SPECIFIC __init__.py CONTENT
# ══════════════════════════════════════════════════════════════

ORCH_INIT_FILES: Dict[str, str] = {
    "shared/__init__.py": '"""Shared domain, ports, schemas, config, and DI container."""\n',
    
    "shared/container/__init__.py": (
        '"""DI Container for orchestrator."""\n'
        'from .container import get_container, cleanup_container, ServiceContainer\n'
    ),

    "shared/config/__init__.py": '"""Configuration management."""\n',

    "chat/__init__.py": '"""Chat feature: routes, agents, services, langgraph."""\n',

    "chat/agents/__init__.py": (
        '"""Chat agents: planner, answer, formatter, orchestrator."""\n'
        'from .base import (\n'
        '    SpecializedAgent,\n'
        '    AgentConfig,\n'
        '    AgentType,\n'
        '    AnswerResult,\n'
        ')\n'
        'from .smart_planner_agent import SmartPlannerAgent, SmartPlanResult\n'
        'from .answer_agent import AnswerAgent\n'
        'from .response_formatter_agent import ResponseFormatterAgent, FormattedResponseResult\n'
        'from .optimized_orchestrator import OptimizedMultiAgentOrchestrator\n'
        '\n'
        '__all__ = [\n'
        '    "SpecializedAgent",\n'
        '    "AgentConfig",\n'
        '    "AgentType",\n'
        '    "AnswerResult",\n'
        '    "SmartPlannerAgent",\n'
        '    "SmartPlanResult",\n'
        '    "AnswerAgent",\n'
        '    "ResponseFormatterAgent",\n'
        '    "FormattedResponseResult",\n'
        '    "OptimizedMultiAgentOrchestrator",\n'
        ']\n'
    ),

    "chat/services/__init__.py": '"""Chat services: orchestration, IRCoT, context, planner."""\n',

    "chat/langgraph/__init__.py": '"""LangGraph workflow for IRCoT orchestration."""\n',

    "chat/adapters/__init__.py": '"""External adapters for chat: OpenRouter LLM, RAG service."""\n',

    "conversation/__init__.py": '"""Conversation management feature."""\n',

    "reasoning/__init__.py": (
        '"""\n'
        'Reasoning feature: symbolic + graph reasoning.\n'
        '\n'
        'Components:\n'
        '- GraphReasoningAgent: ReAct-based graph reasoning\n'
        '- SymbolicReasoningAgent: Rule-based symbolic reasoning\n'
        '- SymbolicReasoningEngine: Core reasoning engine\n'
        '- ReasoningRules: Legal reasoning rules (R001-R008)\n'
        '- QueryAnalyzer: NL query analysis\n'
        '- ContextEnricher: Context enrichment for LLM\n'
        '- SymbolicGraphExtension: Neo4j adapter extension\n'
        '"""\n'
        '\n'
        'from .symbolic_engine import SymbolicReasoningEngine, ReasoningMode\n'
        'from .reasoning_rules import (\n'
        '    ReasoningRule,\n'
        '    ReasoningRuleRegistry,\n'
        '    LEGAL_REASONING_RULES\n'
        ')\n'
        'from .query_analyzer import QueryAnalyzer, QueryComponents\n'
        'from .context_enricher import ContextEnricher\n'
        'from .symbolic_graph_extension import SymbolicGraphExtension\n'
        'from .graph_reasoning_agent import GraphReasoningAgent, GraphQueryType, GraphReasoningResult\n'
        'from .symbolic_reasoning_agent import (\n'
        '    SymbolicReasoningAgent,\n'
        '    SymbolicReasoningResult,\n'
        '    SymbolicQueryType\n'
        ')\n'
        '\n'
        '__all__ = [\n'
        '    "SymbolicReasoningEngine",\n'
        '    "ReasoningMode",\n'
        '    "ReasoningRule",\n'
        '    "ReasoningRuleRegistry",\n'
        '    "LEGAL_REASONING_RULES",\n'
        '    "QueryAnalyzer",\n'
        '    "QueryComponents",\n'
        '    "ContextEnricher",\n'
        '    "SymbolicGraphExtension",\n'
        '    "GraphReasoningAgent",\n'
        '    "GraphQueryType",\n'
        '    "GraphReasoningResult",\n'
        '    "SymbolicReasoningAgent",\n'
        '    "SymbolicReasoningResult",\n'
        '    "SymbolicQueryType",\n'
        ']\n'
    ),

    "admin/__init__.py": '"""Admin feature: health, debug endpoints."""\n',
}


RAG_INIT_FILES: Dict[str, str] = {
    "app/shared/__init__.py": '"""Shared config, container, schemas, utils."""\n',
    "app/shared/config/__init__.py": '"""Configuration."""\n',
    "app/shared/schemas/__init__.py": '"""Shared schemas."""\n',
    "app/shared/utils/__init__.py": '"""Shared utilities."""\n',
    "app/shared/container/__init__.py": (
        '"""DI Container."""\n'
        'from .container import DIContainer, get_container, get_search_service, reset_container\n'
    ),
    "app/search/__init__.py": '"""Search & retrieval feature."""\n',
    "app/search/services/__init__.py": '"""Search services."""\n',
    "app/search/adapters/__init__.py": '"""Search adapters: vector, keyword, reranker."""\n',
    "app/search/ports/__init__.py": '"""Search ports/interfaces."""\n',
    "app/ingest/__init__.py": '"""Document ingestion feature."""\n',
    "app/ingest/services/__init__.py": '"""Ingestion services."""\n',
    "app/ingest/indexing/__init__.py": '"""Indexing modules."""\n',
    "app/ingest/loaders/__init__.py": '"""Document loaders."""\n',
    "app/ingest/store/__init__.py": '"""Storage backends."""\n',
    "app/extraction/__init__.py": '"""KG extraction feature."""\n',
    "app/extraction/pipeline/__init__.py": '"""Extraction pipeline components."""\n',
    "app/knowledge_graph/__init__.py": '"""Knowledge graph feature."""\n',
    "app/knowledge_graph/domain/__init__.py": '"""KG domain models."""\n',
    "app/knowledge_graph/services/__init__.py": '"""KG services."""\n',
    "app/knowledge_graph/adapters/__init__.py": '"""KG adapters (Neo4j)."""\n',
    "app/knowledge_graph/ports/__init__.py": '"""KG ports/interfaces."""\n',
    "app/embedding/__init__.py": '"""Embedding feature."""\n',
    "app/admin/__init__.py": '"""Admin feature."""\n',
    "app/health/__init__.py": '"""Health monitoring feature."""\n',
    "app/llm/__init__.py": '"""LLM client adapters."""\n',
}


# ══════════════════════════════════════════════════════════════
#  NEW main.py FOR ORCHESTRATOR
# ══════════════════════════════════════════════════════════════

ORCH_NEW_ROUTES_INIT = """\
\"\"\"
Orchestrator API routes - Package by Feature.

Combines all feature routers into one ``router`` for the FastAPI app.
\"\"\"

from fastapi import APIRouter

from ..chat.routes import router as chat_router
from ..conversation.routes import router as conversation_router
from ..admin.routes import router as admin_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(conversation_router)
router.include_router(admin_router)
"""

ORCH_NEW_MAIN_IMPORTS = {
    "from .api.routes import router as api_router":
    "from .chat.routes import router as chat_router\nfrom .conversation.routes import router as conversation_router\nfrom .admin.routes import router as admin_router",
    
    "from .core.DI.container import cleanup_container, get_container":
    "from .shared.container.container import cleanup_container, get_container",
    
    "app.include_router(api_router, prefix=\"/api/v1\")":
    "app.include_router(chat_router, prefix=\"/api/v1\")\n    app.include_router(conversation_router, prefix=\"/api/v1\")\n    app.include_router(admin_router, prefix=\"/api/v1\")",
}


# ══════════════════════════════════════════════════════════════
#  MAIN EXECUTION
# ══════════════════════════════════════════════════════════════

def refactor_orchestrator(dry_run: bool):
    print("\n" + "=" * 70)
    print("  ORCHESTRATOR: Package-by-Feature Refactoring")
    print("=" * 70)
    
    app_dir = ORCH / "app"
    
    # 1. Clean __pycache__
    print("\n── Step 1: Clean __pycache__ ──")
    cleanup_pycache(app_dir, dry_run)
    
    # 2. Move files
    print("\n── Step 2: Move files to new structure ──")
    for old_rel, new_rel in ORCH_MOVES:
        if new_rel is None:
            continue
        src = app_dir / old_rel
        dst = app_dir / new_rel
        move_file(src, dst, dry_run)
    
    # 3. Create __init__.py files with proper content
    print("\n── Step 3: Create __init__.py files ──")
    for rel_path, content in ORCH_INIT_FILES.items():
        init_path = app_dir / rel_path
        if dry_run:
            print(f"  📄 Would create: {init_path.relative_to(ROOT)}")
        else:
            init_path.parent.mkdir(parents=True, exist_ok=True)
            init_path.write_text(content)
            print(f"  📄 Created: {init_path.relative_to(ROOT)}")
    
    # 4. Update imports in all new files
    print("\n── Step 4: Update imports ──")
    updated = 0
    for dirpath, _, filenames in os.walk(app_dir):
        for fn in filenames:
            if fn.endswith(".py"):
                fp = Path(dirpath) / fn
                updated += rewrite_imports_in_file(fp, ORCH_IMPORT_REWRITES, dry_run)
    print(f"  Total files updated: {updated}")
    
    # 5. Update main.py specifically
    print("\n── Step 5: Update main.py ──")
    main_py = app_dir / "main.py"
    if main_py.exists():
        text = main_py.read_text()
        for old, new in ORCH_NEW_MAIN_IMPORTS.items():
            text = text.replace(old, new)
        if dry_run:
            print(f"  📝 Would update: {main_py.relative_to(ROOT)}")
        else:
            main_py.write_text(text)
            print(f"  📝 Updated: {main_py.relative_to(ROOT)}")
    
    # 6. Create backward-compat wrappers
    print("\n── Step 6: Create backward-compatibility wrappers ──")
    compat_agents_init = app_dir / "agents" / "__init__.py"
    compat_content = (
        '"""\n'
        'Backward-compatibility re-export wrapper.\n'
        'Canonical code lives in chat.agents and reasoning.\n'
        '"""\n'
        'from ..chat.agents import (  # noqa: F401\n'
        '    SpecializedAgent,\n'
        '    AgentConfig,\n'
        '    AgentType,\n'
        '    AnswerResult,\n'
        '    SmartPlannerAgent,\n'
        '    SmartPlanResult,\n'
        '    AnswerAgent,\n'
        '    ResponseFormatterAgent,\n'
        '    FormattedResponseResult,\n'
        '    OptimizedMultiAgentOrchestrator,\n'
        ')\n'
        'from ..reasoning import (  # noqa: F401\n'
        '    GraphReasoningAgent,\n'
        '    GraphQueryType,\n'
        '    GraphReasoningResult,\n'
        '    SymbolicReasoningAgent,\n'
        '    SymbolicReasoningResult,\n'
        '    SymbolicQueryType,\n'
        ')\n'
    )
    if dry_run:
        print(f"  📄 Would create compat wrapper: {compat_agents_init.relative_to(ROOT)}")
    else:
        compat_agents_init.parent.mkdir(parents=True, exist_ok=True)
        compat_agents_init.write_text(compat_content)
        print(f"  📄 Created compat wrapper: {compat_agents_init.relative_to(ROOT)}")

    # Ensure all __init__.py exist
    print("\n── Step 7: Ensure all __init__.py exist ──")
    create_init_files(app_dir, dry_run)
    
    # 7. Remove old empty dirs (only if not dry_run)
    if not dry_run:
        print("\n── Step 8: Remove old source files ──")
        for old_rel, new_rel in ORCH_MOVES:
            if new_rel is not None:
                old_file = app_dir / old_rel
                if old_file.exists() and old_file.is_file():
                    old_file.unlink()
                    print(f"  🗑️  Removed old: {old_file.relative_to(ROOT)}")
        
        print("\n── Step 9: Cleanup empty dirs ──")
        cleanup_empty_dirs(app_dir, dry_run)


def refactor_rag_services(dry_run: bool):
    print("\n" + "=" * 70)
    print("  RAG SERVICES: Package-by-Feature Refactoring")
    print("=" * 70)
    
    # 1. Clean __pycache__
    print("\n── Step 1: Clean __pycache__ ──")
    cleanup_pycache(RAG, dry_run)
    
    # 2. Move files
    print("\n── Step 2: Move files to new structure ──")
    for old_rel, new_rel in RAG_MOVES:
        if new_rel is None:
            continue
        src = RAG / old_rel
        dst = RAG / new_rel
        move_file(src, dst, dry_run)
    
    # 3. Create __init__.py files  
    print("\n── Step 3: Create __init__.py files ──")
    for rel_path, content in RAG_INIT_FILES.items():
        init_path = RAG / rel_path
        if dry_run:
            print(f"  📄 Would create: {init_path.relative_to(ROOT)}")
        else:
            init_path.parent.mkdir(parents=True, exist_ok=True)
            init_path.write_text(content)
            print(f"  📄 Created: {init_path.relative_to(ROOT)}")
    
    # 4. Update imports
    print("\n── Step 4: Update imports ──")
    updated = 0
    for dirpath, _, filenames in os.walk(RAG):
        for fn in filenames:
            if fn.endswith(".py"):
                fp = Path(dirpath) / fn
                updated += rewrite_imports_in_file(fp, RAG_IMPORT_REWRITES, dry_run)
    print(f"  Total files updated: {updated}")
    
    # 5. Update main.py
    print("\n── Step 5: Update main.py ──")
    main_py = RAG / "app" / "main.py"
    if main_py.exists():
        text = main_py.read_text()
        # The main.py uses absolute imports - these should be caught by the general rewrite
        if dry_run:
            print(f"  📝 main.py will be updated by import rewrites")
        else:
            print(f"  📝 main.py updated by import rewrites")
    
    # 6. Ensure all __init__.py exist
    print("\n── Step 6: Ensure all __init__.py exist ──")
    create_init_files(RAG / "app", dry_run)
    
    # 7. Remove old files and empty dirs
    if not dry_run:
        print("\n── Step 7: Remove old source files ──")
        for old_rel, new_rel in RAG_MOVES:
            if new_rel is not None:
                old_file = RAG / old_rel
                if old_file.exists() and old_file.is_file():
                    old_file.unlink()
                    print(f"  🗑️  Removed old: {old_file.relative_to(ROOT)}")
        
        print("\n── Step 8: Cleanup empty dirs ──")
        cleanup_empty_dirs(RAG, dry_run)


def print_target_structure():
    print("""
╔══════════════════════════════════════════════════════════════╗
║         TARGET STRUCTURE: Package by Feature                ║
╚══════════════════════════════════════════════════════════════╝

📁 orchestrator/app/
├── main.py
├── shared/                          # 🔧 Shared kernel
│   ├── domain.py                    #    Domain models
│   ├── exceptions.py                #    Domain exceptions
│   ├── ports.py                     #    Port interfaces
│   ├── schemas.py                   #    API schemas
│   ├── config/                      #    Configuration
│   │   ├── config_manager.py
│   │   └── ircot_config.py
│   └── container/                   #    DI Container
│       ├── container.py
│       ├── port_providers.py
│       ├── graph_providers.py
│       ├── orchestration_providers.py
│       └── agent_factory.py
├── chat/                            # 💬 Chat feature
│   ├── routes.py                    #    API endpoints
│   ├── response_mappers.py
│   ├── exception_handlers.py
│   ├── agents/                      #    Chat agents
│   │   ├── base.py
│   │   ├── answer_agent.py
│   │   ├── smart_planner_agent.py
│   │   ├── response_formatter_agent.py
│   │   └── optimized_orchestrator.py
│   ├── services/                    #    Business logic
│   │   ├── orchestration_service.py
│   │   ├── ircot_service.py
│   │   ├── context_service.py
│   │   └── planner_service.py
│   ├── langgraph/                   #    LangGraph workflow
│   │   ├── nodes.py
│   │   ├── state.py
│   │   └── workflow.py
│   └── adapters/                    #    External adapters
│       ├── openrouter_adapter.py
│       └── rag_adapter.py
├── conversation/                    # 🗣️ Conversation feature
│   ├── routes.py
│   └── conversation_manager.py
├── reasoning/                       # 🧠 Reasoning feature
│   ├── graph_reasoning_agent.py
│   ├── symbolic_reasoning_agent.py
│   ├── symbolic_engine.py
│   ├── reasoning_rules.py
│   ├── query_analyzer.py
│   ├── context_enricher.py
│   └── symbolic_graph_extension.py
└── admin/                           # ⚙️ Admin feature
    └── routes.py

📁 rag_services/app/
├── main.py
├── shared/                          # 🔧 Shared kernel
│   ├── config/
│   │   ├── settings.py
│   │   └── logging.py
│   ├── container/
│   │   ├── container.py
│   │   └── ingest_factory.py
│   ├── schemas/
│   │   ├── common.py
│   │   └── doc.py
│   └── utils/
│       └── json_utils.py
├── search/                          # 🔍 Search feature
│   ├── routes.py
│   ├── schemas.py
│   ├── retrieval_routes.py
│   ├── retrieval_schemas.py
│   ├── services/
│   │   ├── search_service.py
│   │   └── api_facade.py
│   ├── retrieval/
│   │   ├── legal_query_parser.py
│   │   ├── metadata_filter_builder.py
│   │   ├── neighbor_expander.py
│   │   ├── schemas.py
│   │   └── unified_retriever.py
│   ├── adapters/
│   │   ├── weaviate_vector_adapter.py
│   │   ├── opensearch_keyword_adapter.py
│   │   ├── cross_encoder_reranker.py
│   │   ├── llamaindex/
│   │   └── mappers/
│   └── ports/
│       ├── repositories.py
│       └── services.py
├── ingest/                          # 📥 Ingest feature
│   ├── routes.py
│   ├── schemas.py
│   ├── opensearch_routes.py
│   ├── services/
│   │   ├── ingest_service.py
│   │   ├── legal_ingestion_service.py
│   │   └── job_store.py
│   ├── indexing/
│   │   ├── graph_builder.py
│   │   ├── index_opensearch_data.py
│   │   └── index_semantic_data.py
│   ├── loaders/
│   │   ├── llamaindex_legal_parser.py
│   │   └── vietnam_legal_docx_parser.py
│   └── store/
│       ├── opensearch/
│       └── vector/
├── extraction/                      # 📄 Extraction feature
│   ├── routes.py
│   └── pipeline/
│       ├── cleaner.py
│       ├── llamaindex_extractor.py
│       ├── page_merger.py
│       └── schemas.py
├── knowledge_graph/                 # 🕸️ Knowledge Graph feature
│   ├── routes.py
│   ├── domain/
│   │   └── graph_models.py
│   ├── services/
│   │   ├── graph_builder_service.py
│   │   └── graph_builder_config.py
│   ├── adapters/
│   │   └── neo4j_adapter.py
│   └── ports/
│       └── graph_repository.py
├── embedding/                       # 🧬 Embedding feature
│   ├── routes.py
│   └── schemas.py
├── admin/                           # ⚙️ Admin feature
│   └── routes.py
├── health/                          # 🏥 Health monitoring
│   ├── routes.py
│   └── health_v2.py
└── llm/                             # 🤖 LLM clients
    ├── gemini_client.py
    ├── openai_client.py
    └── openrouter_client.py
""")


def main():
    parser = argparse.ArgumentParser(
        description="Refactor to Package-by-Feature structure"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply changes (default: dry-run)"
    )
    parser.add_argument(
        "--orch-only",
        action="store_true", 
        help="Only refactor orchestrator"
    )
    parser.add_argument(
        "--rag-only",
        action="store_true",
        help="Only refactor rag_services"
    )
    args = parser.parse_args()

    dry_run = not args.apply

    if dry_run:
        print("\n🔍 DRY RUN MODE — no files will be modified")
        print("   Run with --apply to actually perform the refactoring\n")
    else:
        print("\n⚡ APPLY MODE — files will be moved and imports updated")
        print("   Make sure you have committed your current changes!\n")

    print_target_structure()

    if not args.rag_only:
        refactor_orchestrator(dry_run)
    
    if not args.orch_only:
        refactor_rag_services(dry_run)

    if dry_run:
        print("\n" + "=" * 70)
        print("  DRY RUN COMPLETE — review the plan above")
        print("  Run with --apply to execute:  python refactor_to_package_by_feature.py --apply")
        print("  Rollback:  git checkout -- services/orchestrator services/rag_services")
        print("=" * 70 + "\n")
    else:
        print("\n" + "=" * 70)
        print("  ✅ REFACTORING COMPLETE!")
        print("  Please verify the changes and fix any remaining import issues.")
        print("  Rollback:  git checkout -- services/orchestrator services/rag_services")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
