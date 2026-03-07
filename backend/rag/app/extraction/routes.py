"""
API Routes for Knowledge Graph Extraction Pipeline.

Provides endpoints for:
- LlamaIndex extraction: Modern PDF extraction using LlamaParse + PropertyGraphIndex (RECOMMENDED)
- Stage 1: Upload PDF and extract structure (VLM only) - DEPRECATED
- Stage 2: Upload Stage 1 JSON and extract semantics (LLM) - DEPRECATED
- Full pipeline: Combined VLM + LLM - DEPRECATED
- Get extraction status
- Download extraction results

MIGRATION NOTICE:
    The VLM-based extraction (Stage 1/Stage 2/Full pipeline) is deprecated.
    Please use the new LlamaIndex-based extraction endpoint: POST /api/v1/extraction/llamaindex
    
    Benefits of LlamaIndex extraction:
    - Cloud-based LlamaParse (no local GPU needed)
    - Better table handling across page boundaries
    - Automatic entity/relation extraction using GPT-4o
    - Direct Neo4j integration
    
    Set USE_LLAMAINDEX_EXTRACTION=true in your environment to enable.
"""

import os
import json
import asyncio
import uuid
import shutil
import logging
import warnings
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

# Configure logging
logger = logging.getLogger(__name__)

# Load .env file for Neo4j credentials
from dotenv import load_dotenv
load_dotenv()

# Check for LlamaIndex extraction mode
USE_LLAMAINDEX_EXTRACTION = os.getenv("USE_LLAMAINDEX_EXTRACTION", "true").lower() in ("true", "1", "yes")

router = APIRouter(prefix="/extraction", tags=["Knowledge Graph Extraction"])

# Store extraction jobs status
extraction_jobs: Dict[str, Dict[str, Any]] = {}

# Paths
BASE_DIR = Path(__file__).parent.parent.parent.parent.parent  # rag_services/
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
RESULTS_DIR = BASE_DIR / "data" / "extraction_results"
SCRIPTS_DIR = BASE_DIR / "scripts"

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


class ExtractionRequest(BaseModel):
    """Request model for extraction."""
    category: str = "Quy chế Đào tạo"
    push_to_neo4j: bool = False


class LlamaIndexExtractionRequest(BaseModel):
    """Request model for LlamaIndex-based extraction."""
    push_to_neo4j: bool = False
    extract_kg: bool = True  # Whether to extract entities/relations


class ExtractionStatus(BaseModel):
    """Status of an extraction job."""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    current_step: str
    stage: str = "full"  # stage1, stage2, full, llamaindex
    created_at: str
    completed_at: Optional[str] = None
    result_file: Optional[str] = None
    error: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None


class Stage2Request(BaseModel):
    """Request model for Stage 2 extraction."""
    stage1_data: Dict[str, Any]
    category: str = "Quy chế Đào tạo"
    push_to_neo4j: bool = False


def get_extraction_status(job_id: str) -> Optional[ExtractionStatus]:
    """Get status of an extraction job."""
    if job_id not in extraction_jobs:
        return None
    return ExtractionStatus(**extraction_jobs[job_id])


# =============================================================================
# LlamaIndex Extraction (NEW - RECOMMENDED)
# =============================================================================

@router.post("/llamaindex", response_model=ExtractionStatus)
async def start_llamaindex_extraction(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    push_to_neo4j: bool = False,
    extract_kg: bool = True,
):
    """
    Extract knowledge graph from PDF using LlamaParse + PropertyGraphIndex.
    
    This is the RECOMMENDED extraction method that replaces the VLM-based pipeline.
    
    Features:
    - Cloud-based LlamaParse API (no local GPU required)
    - Handles complex tables across page boundaries
    - Automatic entity/relation extraction using GPT-4o
    - Direct Neo4j integration
    
    Args:
        file: PDF file to process
        push_to_neo4j: Whether to push extracted graph to Neo4j
        extract_kg: Whether to run entity/relation extraction
        
    Returns:
        ExtractionStatus with job_id for tracking
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400, 
            detail="Only PDF files are supported for LlamaIndex extraction"
        )
    
    # Generate job ID
    job_id = str(uuid.uuid4())[:8]
    
    # Save uploaded file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = file.filename.replace(" ", "_")
    file_path = UPLOAD_DIR / f"{timestamp}_{job_id}_{safe_name}"
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Initialize job status
    extraction_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "current_step": "Đã nhận file, đang khởi tạo...",
        "stage": "llamaindex",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "result_file": None,
        "error": None,
        "stats": None,
    }
    
    # Start background extraction
    background_tasks.add_task(
        run_llamaindex_pipeline,
        job_id=job_id,
        pdf_path=file_path,
        push_to_neo4j=push_to_neo4j,
        extract_kg=extract_kg,
    )
    
    return ExtractionStatus(**extraction_jobs[job_id])


async def run_llamaindex_pipeline(
    job_id: str,
    pdf_path: Path,
    push_to_neo4j: bool,
    extract_kg: bool,
):
    """
    Run LlamaIndex-based extraction pipeline.
    
    Uses LlamaParse for document parsing and PropertyGraphIndex for KG extraction.
    """
    try:
        extraction_jobs[job_id]["status"] = "processing"
        extraction_jobs[job_id]["current_step"] = "Đang khởi tạo LlamaIndex..."
        extraction_jobs[job_id]["progress"] = 10
        
        # Import LlamaIndex extraction service
        from app.extraction.llamaindex_extractor import LlamaIndexExtractionService
        
        # Initialize service
        service = LlamaIndexExtractionService.from_env()
        
        extraction_jobs[job_id]["current_step"] = "Đang parse PDF với LlamaParse..."
        extraction_jobs[job_id]["progress"] = 30
        
        # Run extraction
        result = await service.extract_from_pdf(pdf_path, document_id=job_id)
        
        extraction_jobs[job_id]["current_step"] = f"Đã extract {len(result.parsed_document.chunks)} chunks"
        extraction_jobs[job_id]["progress"] = 60
        
        # Prepare output
        output_data = {
            "job_id": job_id,
            "document_id": result.document_id,
            "extraction_method": "llamaindex",
            "parsed_document": {
                "content_preview": result.parsed_document.content[:1000] + "..." if len(result.parsed_document.content) > 1000 else result.parsed_document.content,
                "tables": result.parsed_document.tables,
                "chunks": result.parsed_document.chunks,
                "pages": result.parsed_document.pages,
            },
            "entities": [
                {
                    "id": e.id,
                    "type": e.type.value if hasattr(e.type, 'value') else str(e.type),
                    "text": e.text,
                    "normalized": e.normalized,
                    "source_chunk": e.source_chunk_id,
                }
                for e in result.entities
            ],
            "relations": [
                {
                    "source_id": r.source_id,
                    "target_id": r.target_id,
                    "type": r.type.value if hasattr(r.type, 'value') else str(r.type),
                    "evidence": r.evidence,
                }
                for r in result.relations
            ],
            "errors": result.errors,
            "metadata": result.metadata,
        }
        
        # Save result
        result_file = RESULTS_DIR / f"{job_id}_llamaindex_result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        extraction_jobs[job_id]["progress"] = 80
        
        # Push to Neo4j if requested
        if push_to_neo4j and (result.entities or result.relations):
            extraction_jobs[job_id]["current_step"] = "Đang đẩy dữ liệu lên Neo4j..."
            
            try:
                from app.knowledge_graph.stores.neo4j_store import Neo4jGraphAdapter
                from app.shared.config.settings import settings
                
                adapter = Neo4jGraphAdapter(
                    uri=settings.neo4j_uri,
                    username=settings.neo4j_username,
                    password=settings.neo4j_password,
                )
                
                # Convert to graph models
                nodes, rels = result.to_graph_models()
                
                # Store to Neo4j
                for node in nodes:
                    await adapter.add_node(node)
                
                for rel in rels:
                    await adapter.add_relationship(rel)
                
                adapter.close()
                
                logger.info(f"Pushed {len(nodes)} nodes, {len(rels)} relations to Neo4j")
                
            except Exception as e:
                logger.error(f"Neo4j push failed: {e}")
                result.errors.append(f"Neo4j push failed: {str(e)}")
        
        # Complete
        extraction_jobs[job_id]["status"] = "completed"
        extraction_jobs[job_id]["progress"] = 100
        extraction_jobs[job_id]["current_step"] = "Hoàn thành!"
        extraction_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        extraction_jobs[job_id]["result_file"] = str(result_file)
        extraction_jobs[job_id]["stats"] = {
            "chunks": len(result.parsed_document.chunks),
            "tables": len(result.parsed_document.tables),
            "entities": len(result.entities),
            "relations": len(result.relations),
            "pages": result.parsed_document.pages,
            "errors": len(result.errors),
        }
        
        logger.info(
            f"LlamaIndex extraction completed for job {job_id}: "
            f"{len(result.entities)} entities, {len(result.relations)} relations"
        )
        
    except Exception as e:
        logger.exception(f"LlamaIndex extraction failed for job {job_id}")
        extraction_jobs[job_id]["status"] = "failed"
        extraction_jobs[job_id]["error"] = str(e)
        extraction_jobs[job_id]["current_step"] = f"Lỗi: {str(e)}"
        
    finally:
        # Cleanup uploaded file
        try:
            if pdf_path.exists():
                pdf_path.unlink()
        except Exception:
            pass


# =============================================================================
# Stage 2: LLM Semantic Extraction (DEPRECATED - FIXED TABLE MERGE)
# =============================================================================

async def run_stage2_pipeline(
    job_id: str,
    stage1_data: Dict[str, Any],
    category: str,
    push_to_neo4j: bool
):
    """
    Run Stage 2: LLM for semantic extraction from Stage 1 results.
    Input: Stage 1 JSON (structure)
    Output: Combined JSON with structure + semantics
    
    DEPRECATED: Use LlamaIndex extraction instead.
    """
    warnings.warn(
        "Stage 2 pipeline is deprecated. Use /api/v1/extraction/llamaindex instead.",
        DeprecationWarning
    )
    
    try:
        extraction_jobs[job_id]["status"] = "processing"
        extraction_jobs[job_id]["current_step"] = "Đang khởi tạo LLM..."
        extraction_jobs[job_id]["progress"] = 10
        
        # Import extraction modules (deprecated - use LlamaIndex endpoint instead)
        from app.extraction.deprecated.hybrid_extractor import SemanticExtractor, LLMConfig
        
        loop = asyncio.get_event_loop()
        
        # Initialize LLM extractor
        llm_config = LLMConfig.from_env()
        semantic_extractor = SemanticExtractor(llm_config)
        
        # 1. Parse Input & Validate
        if "stage1_structure" in stage1_data:
            structure = stage1_data["stage1_structure"]
        elif "structure" in stage1_data:
            structure = stage1_data["structure"]
        else:
            structure = stage1_data

        articles = structure.get("articles", [])
        clauses = structure.get("clauses", [])
        tables = structure.get("tables", [])
        relations = structure.get("relations", [])
        
        if not articles:
            raise ValueError(f"Không tìm thấy điều khoản trong dữ liệu Stage 1. Keys: {list(stage1_data.keys())}")
        
        # 2. CRITICAL: MERGE CLAUSES AND TABLES INTO ARTICLES LOGIC
        # ---------------------------------------------------------------------
        extraction_jobs[job_id]["current_step"] = f"Đang gộp {len(clauses)} khoản và {len(tables)} bảng vào văn bản..."
        
        # Map article by ID
        article_map = {a['id']: a for a in articles}
        
        # Map Child -> Parent from relations
        child_to_parent = {}
        for rel in relations:
            if rel.get("type") == "CONTAINS":
                child_to_parent[rel["target"]] = rel["source"]
        
        # MERGE CLAUSES INTO ARTICLES
        clause_merged_count = 0
        for clause in clauses:
            parent_id = child_to_parent.get(clause["id"])
            if parent_id and parent_id in article_map:
                parent_article = article_map[parent_id]
                # Append Clause content to Article Text
                clause_title = clause.get('title', '')
                clause_text = clause.get('full_text', '')
                append_text = f"\n\n--- {clause_title} ---\n{clause_text}\n"
                parent_article["full_text"] += append_text
                clause_merged_count += 1
        
        print(f"Job {job_id}: Successfully merged {clause_merged_count} clauses into articles.")
        
        # MERGE TABLES INTO ARTICLES
        table_merged_count = 0
        for table in tables:
            parent_id = child_to_parent.get(table["id"])
            if parent_id and parent_id in article_map:
                parent_article = article_map[parent_id]
                # Append Markdown Table to Article Text
                append_text = f"\n\n=== BẢNG THAM CHIẾU ({table.get('title', 'Bảng')}) ===\n{table.get('full_text', '')}\n========================\n"
                parent_article["full_text"] += append_text
                table_merged_count += 1
        
        print(f"Job {job_id}: Successfully merged {table_merged_count} tables into articles.")
        # ---------------------------------------------------------------------

        extraction_jobs[job_id]["progress"] = 20
        extraction_jobs[job_id]["current_step"] = f"Đang xử lý {len(articles)} điều..."
        
        # Process articles in parallel
        MAX_CONCURRENT = 5
        all_entities = []
        all_relations = []
        all_modifications = []
        errors = []
        
        async def process_article(article):
            try:
                print(f"[Stage2] Processing article: {article.get('id', 'unknown')}, text length: {len(article.get('full_text', ''))}")
                
                article_result = await loop.run_in_executor(
                    None,
                    lambda: semantic_extractor.extract_from_article(
                        article_id=article.get('id', ''),
                        article_title=article.get('title', ''),
                        article_text=article.get('full_text', '') # Text đã có bảng
                    )
                )
                
                print(f"[Stage2] Result type for {article.get('id', '')}: {type(article_result)}")
                
                if hasattr(article_result, 'model_dump'):
                    article_dict = article_result.model_dump()
                    print(f"[Stage2] model_dump keys: {article_dict.keys()}")
                else:
                    article_dict = article_result if isinstance(article_result, dict) else {}
                    print(f"[Stage2] Direct dict keys: {article_dict.keys() if article_dict else 'empty'}")
                
                entities = []
                for entity in article_dict.get('nodes', []):
                    entity['source_article_id'] = article.get('id', '')
                    entities.append(entity)
                
                relations = []
                for rel in article_dict.get('relations', []):
                    rel['source_article_id'] = article.get('id', '')
                    relations.append(rel)
                
                # Collect modifications (for amendment documents)
                modifications = article_dict.get('modifications', [])
                
                print(f"[Stage2] {article.get('id', '')}: {len(entities)} entities, {len(relations)} relations, {len(modifications)} modifications")
                
                return {"entities": entities, "relations": relations, "modifications": modifications, "error": None}
                
            except Exception as e:
                import traceback
                print(f"[Stage2] ERROR processing {article.get('id', '')}: {e}")
                print(traceback.format_exc())
                return {"entities": [], "relations": [], "modifications": [], "error": {"article_id": article.get('id', ''), "error": str(e)}}
        
        # Process in batches
        for batch_start in range(0, len(articles), MAX_CONCURRENT):
            batch = articles[batch_start:batch_start + MAX_CONCURRENT]
            batch_tasks = [process_article(article) for article in batch]
            batch_results = await asyncio.gather(*batch_tasks)
            
            for result in batch_results:
                all_entities.extend(result["entities"])
                all_relations.extend(result["relations"])
                all_modifications.extend(result.get("modifications", []))
                if result["error"]:
                    errors.append(result["error"])
            
            processed = min(batch_start + MAX_CONCURRENT, len(articles))
            progress = 20 + int(60 * processed / len(articles)) if articles else 80
            extraction_jobs[job_id]["progress"] = progress
            extraction_jobs[job_id]["current_step"] = f"Stage 2: Đã xử lý {processed}/{len(articles)} điều..."
        
        semantic_result = {
            "entities": all_entities,
            "relations": all_relations,
            "modifications": all_modifications,
            "errors": errors,
            "stats": {
                "entities": len(all_entities),
                "relations": len(all_relations),
                "modifications": len(all_modifications),
                "errors": len(errors)
            }
        }
        
        extraction_jobs[job_id]["progress"] = 85
        extraction_jobs[job_id]["current_step"] = "Đang tổng hợp kết quả..."
        
        # Combine results (merge stage1 + stage2)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        merged_result = {
            "extraction_id": job_id,
            "stage": "merged",
            "source_file": stage1_data.get("source_file", "unknown"),
            "extracted_at": datetime.now().isoformat(),
            "category": category,
            "stage1_structure": structure, # Cấu trúc đã được update text (có bảng)
            "stage2_semantic": semantic_result
        }
        
        result_file = RESULTS_DIR / f"merged_{timestamp}_{job_id[:8]}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(merged_result, f, ensure_ascii=False, indent=2)
        
        extraction_jobs[job_id]["progress"] = 90
        
        # Initialize stats dict before Neo4j push
        neo4j_stats = {}
        
        # Push to Neo4j if requested
        if push_to_neo4j:
            extraction_jobs[job_id]["current_step"] = "Đang đẩy dữ liệu lên Neo4j..."
            try:
                from app.ingest.indexing.graph_builder import Neo4jGraphBuilder
                
                uri = os.getenv("NEO4J_URI", "")
                user = os.getenv("NEO4J_USERNAME", "")
                password = os.getenv("NEO4J_PASSWORD", "")
                
                with Neo4jGraphBuilder(uri=uri, user=user, password=password) as builder:
                    stats = builder.build_graph(
                        extraction_data=merged_result,
                        category=category,
                        clear_first=False
                    )
                    neo4j_stats = {
                        "entities": stats.entities,
                        "merged": stats.entities_merged,
                        "relations": stats.semantic_relations
                    }
            except Exception as e:
                neo4j_stats["neo4j_error"] = str(e)
        
        # Complete
        extraction_jobs[job_id]["status"] = "completed"
        extraction_jobs[job_id]["progress"] = 100
        extraction_jobs[job_id]["current_step"] = "Stage 2 + Merge hoàn thành!"
        extraction_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        extraction_jobs[job_id]["result_file"] = str(result_file.name)
        extraction_jobs[job_id]["stats"] = {
            "articles_processed": len(articles),
            "clauses_merged": clause_merged_count,
            "tables_merged": table_merged_count,
            "entities": len(all_entities),
            "relations": len(all_relations),
            "errors": len(errors),
            "neo4j": neo4j_stats if neo4j_stats else None
        }
        
    except Exception as e:
        import traceback
        extraction_jobs[job_id]["status"] = "failed"
        extraction_jobs[job_id]["error"] = str(e)
        extraction_jobs[job_id]["current_step"] = f"Lỗi: {str(e)}"
        print(f"Stage 2 extraction error: {traceback.format_exc()}")


# =============================================================================
# Full Pipeline (Original - FIXED)
# =============================================================================

async def run_extraction_pipeline(
    job_id: str,
    pdf_path: Path,
    category: str,
    push_to_neo4j: bool
):
    """
    Run the Two-Stage extraction pipeline asynchronously.
    Stage 1: VLM Structure -> Merge Table -> Stage 2: Semantic
    """
    try:
        # Update status
        extraction_jobs[job_id]["status"] = "processing"
        extraction_jobs[job_id]["current_step"] = "Đang chuyển PDF sang ảnh..."
        extraction_jobs[job_id]["progress"] = 10
        
        # Import extraction modules (deprecated - use LlamaIndex endpoint instead)
        from app.extraction.deprecated.hybrid_extractor import StructureExtractor, SemanticExtractor, VLMConfig, LLMConfig
        from pdf2image import convert_from_path
        
        # Convert PDF to images
        images_dir = pdf_path.parent / f"{pdf_path.stem}_images"
        images_dir.mkdir(exist_ok=True)
        
        extraction_jobs[job_id]["current_step"] = "Đang chuyển PDF sang ảnh..."
        
        # Run in executor to not block
        loop = asyncio.get_event_loop()
        pages = await loop.run_in_executor(
            None,
            lambda: convert_from_path(str(pdf_path), dpi=200)
        )
        
        image_paths = []
        for i, page in enumerate(pages):
            img_path = images_dir / f"page_{i+1}.png"
            await loop.run_in_executor(None, lambda p=page, ip=img_path: p.save(str(ip), "PNG"))
            image_paths.append(str(img_path))
        
        extraction_jobs[job_id]["progress"] = 20
        extraction_jobs[job_id]["current_step"] = f"Đã chuyển {len(pages)} trang. Đang khởi tạo extractor..."
        
        # Initialize extractors
        vlm_config = VLMConfig.from_env()
        llm_config = LLMConfig.from_env()
        structure_extractor = StructureExtractor(vlm_config)
        semantic_extractor = SemanticExtractor(llm_config)
        
        # Stage 1: VLM Structure Extraction
        extraction_jobs[job_id]["current_step"] = "Stage 1: Trích xuất cấu trúc với VLM..."
        extraction_jobs[job_id]["progress"] = 30
        
        structure_result = await loop.run_in_executor(
            None,
            lambda: structure_extractor.extract_from_images(image_paths)
        )
        
        # Convert Pydantic model to dict
        if hasattr(structure_result, 'model_dump'):
            structure_dict = structure_result.model_dump()
        else:
            structure_dict = structure_result
        
        # POST-PROCESSING: Auto-fix relations for amendment documents
        from app.extraction.page_merger import auto_fix_amendment_relations
        structure_dict = auto_fix_amendment_relations(structure_dict)
        
        extraction_jobs[job_id]["progress"] = 50
        
        # ---------------------------------------------------------------------
        # CRITICAL: MERGE CLAUSES AND TABLES INTO ARTICLES (Fixes missing data in Stage 2)
        # ---------------------------------------------------------------------
        extraction_jobs[job_id]["current_step"] = "Đang gộp khoản và bảng vào văn bản..."
        
        articles = structure_dict.get('articles', [])
        clauses = structure_dict.get('clauses', [])
        tables = structure_dict.get('tables', [])
        relations = structure_dict.get('relations', [])
        
        article_map = {a['id']: a for a in articles}
        child_to_parent = {r["target"]: r["source"] for r in relations if r["type"] == "CONTAINS"}
        
        # MERGE CLAUSES INTO ARTICLES
        clause_merged = 0
        for clause in clauses:
            parent_id = child_to_parent.get(clause['id'])
            if parent_id and parent_id in article_map:
                clause_title = clause.get('title', '')
                clause_text = clause.get('full_text', '')
                article_map[parent_id]['full_text'] += f"\n\n--- {clause_title} ---\n{clause_text}\n"
                clause_merged += 1
        
        # MERGE TABLES INTO ARTICLES
        table_merged = 0
        for table in tables:
            parent_id = child_to_parent.get(table['id'])
            if parent_id and parent_id in article_map:
                # Update article text with table content
                article_map[parent_id]['full_text'] += f"\n\n=== BẢNG ({table.get('title')}) ===\n{table.get('full_text')}\n"
                table_merged += 1
        
        print(f"Full pipeline: Merged {clause_merged} clauses, {table_merged} tables.")
        # ---------------------------------------------------------------------
        
        # Stage 2: LLM Semantic Extraction
        extraction_jobs[job_id]["current_step"] = "Stage 2: Trích xuất ngữ nghĩa với LLM (song song)..."
        extraction_jobs[job_id]["progress"] = 60
        
        async def process_article(article):
            """Process a single article."""
            try:
                article_result = await loop.run_in_executor(
                    None,
                    lambda: semantic_extractor.extract_from_article(
                        article_id=article.get('id', ''),
                        article_title=article.get('title', ''),
                        article_text=article.get('full_text', '')
                    )
                )
                
                if hasattr(article_result, 'model_dump'):
                    article_dict = article_result.model_dump()
                else:
                    article_dict = article_result if isinstance(article_result, dict) else {}
                
                entities = []
                for entity in article_dict.get('nodes', []):
                    entity['source_article_id'] = article.get('id', '')
                    entities.append(entity)
                
                relations = []
                for rel in article_dict.get('relations', []):
                    rel['source_article_id'] = article.get('id', '')
                    relations.append(rel)
                
                # Collect modifications (for amendment documents)
                modifications = article_dict.get('modifications', [])
                
                return {"entities": entities, "relations": relations, "modifications": modifications, "error": None}
                
            except Exception as e:
                return {"entities": [], "relations": [], "modifications": [], "error": {"article_id": article.get('id', ''), "error": str(e)}}
        
        # Run all articles in parallel
        MAX_CONCURRENT = 5
        all_entities = []
        all_relations = []
        all_modifications = []
        errors = []
        
        for batch_start in range(0, len(articles), MAX_CONCURRENT):
            batch = articles[batch_start:batch_start + MAX_CONCURRENT]
            batch_tasks = [process_article(article) for article in batch]
            batch_results = await asyncio.gather(*batch_tasks)
            
            for result in batch_results:
                all_entities.extend(result["entities"])
                all_relations.extend(result["relations"])
                all_modifications.extend(result.get("modifications", []))
                if result["error"]:
                    errors.append(result["error"])
            
            processed = min(batch_start + MAX_CONCURRENT, len(articles))
            progress = 60 + int(20 * processed / len(articles)) if articles else 80
            extraction_jobs[job_id]["progress"] = progress
            extraction_jobs[job_id]["current_step"] = f"Stage 2: Đã xử lý {processed}/{len(articles)} điều..."
        
        semantic_result = {
            "entities": all_entities,
            "relations": all_relations,
            "modifications": all_modifications,
            "errors": errors,
            "stats": {
                "entities": len(all_entities),
                "relations": len(all_relations),
                "modifications": len(all_modifications),
                "errors": len(errors)
            }
        }
        
        extraction_jobs[job_id]["progress"] = 80
        
        # Combine results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result = {
            "extraction_id": job_id,
            "source_file": pdf_path.name,
            "extracted_at": datetime.now().isoformat(),
            "category": category,
            "stage1_structure": structure_dict,
            "stage2_semantic": semantic_result
        }
        
        # Save result
        result_file = RESULTS_DIR / f"extraction_{timestamp}_{job_id[:8]}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        extraction_jobs[job_id]["progress"] = 90
        
        # Initialize neo4j stats
        neo4j_stats = {}
        
        # Push to Neo4j if requested
        if push_to_neo4j:
            extraction_jobs[job_id]["current_step"] = "Đang đẩy dữ liệu lên Neo4j..."
            try:
                from app.ingest.indexing.graph_builder import Neo4jGraphBuilder
                
                uri = os.getenv("NEO4J_URI", "")
                user = os.getenv("NEO4J_USERNAME", "")
                password = os.getenv("NEO4J_PASSWORD", "")
                
                with Neo4jGraphBuilder(uri=uri, user=user, password=password) as builder:
                    stats = builder.build_graph(
                        extraction_data=result,
                        category=category,
                        clear_first=False
                    )
                    neo4j_stats = {
                        "entities": stats.entities,
                        "merged": stats.entities_merged,
                        "relations": stats.semantic_relations
                    }
            except Exception as e:
                neo4j_stats["neo4j_error"] = str(e)
        
        # Complete
        extraction_jobs[job_id]["status"] = "completed"
        extraction_jobs[job_id]["progress"] = 100
        extraction_jobs[job_id]["current_step"] = "Hoàn thành!"
        extraction_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        extraction_jobs[job_id]["result_file"] = str(result_file.name)
        extraction_jobs[job_id]["stats"] = {
            "pages": len(pages),
            "articles": len(structure_dict.get("articles", [])),
            "clauses_merged": clause_merged,
            "tables_merged": table_merged,
            "entities": semantic_result.get("stats", {}).get("entities", 0),
            "relations": semantic_result.get("stats", {}).get("relations", 0),
            "neo4j": neo4j_stats if neo4j_stats else None
        }
        
        # Cleanup images
        shutil.rmtree(images_dir, ignore_errors=True)
        
    except Exception as e:
        import traceback
        extraction_jobs[job_id]["status"] = "failed"
        extraction_jobs[job_id]["error"] = str(e)
        extraction_jobs[job_id]["current_step"] = f"Lỗi: {str(e)}"
        print(f"Extraction error: {traceback.format_exc()}")


@router.post("/upload", response_model=ExtractionStatus)
async def upload_and_extract(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = "Quy chế Đào tạo",
    push_to_neo4j: bool = False
):
    """
    Upload a PDF file and start knowledge graph extraction.
    
    Returns a job ID to track progress.
    """
    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file PDF")
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save uploaded file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    pdf_path = UPLOAD_DIR / safe_filename
    
    try:
        with open(pdf_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lưu file: {str(e)}")
    
    # Initialize job status
    extraction_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "current_step": "Đang khởi tạo...",
        "stage": "full",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "result_file": None,
        "error": None,
        "stats": None
    }
    
    # Start extraction in background
    background_tasks.add_task(
        run_extraction_pipeline,
        job_id,
        pdf_path,
        category,
        push_to_neo4j
    )
    
    return ExtractionStatus(**extraction_jobs[job_id])


# =============================================================================
# Stage 1: HYBRID Mode - LlamaParse + VLM
# =============================================================================

# Check if hybrid mode is enabled
USE_HYBRID_EXTRACTION = os.getenv("USE_HYBRID_EXTRACTION", "false").lower() in ("true", "1", "yes")


async def run_hybrid_stage1_pipeline(
    job_id: str,
    pdf_path: Path,
    category: str
):
    """
    Run Hybrid Stage 1: LlamaParse for text + VLM for structure verification.
    
    This mode combines:
    - LlamaParse: Superior OCR quality, table extraction
    - VLM: Accurate structure boundaries (chapter/article detection)
    
    Benefits over pure VLM:
    - Better text extraction quality
    - Better table handling
    - Lower API costs (VLM only for verification, not all content)
    - Handles multi-page content correctly
    """
    try:
        extraction_jobs[job_id]["status"] = "processing"
        extraction_jobs[job_id]["current_step"] = "Đang khởi tạo LlamaParse + VLM hybrid..."
        extraction_jobs[job_id]["progress"] = 5
        
        # Import hybrid extractor (deprecated - use LlamaIndex endpoint instead)
        from app.extraction.deprecated.hybrid_llamaparse_vlm import HybridExtractor
        
        loop = asyncio.get_event_loop()
        
        # Initialize hybrid extractor
        extraction_jobs[job_id]["current_step"] = "Đang khởi tạo hybrid extractor..."
        extraction_jobs[job_id]["progress"] = 10
        
        extractor = HybridExtractor.from_env()
        
        # Run hybrid extraction
        extraction_jobs[job_id]["current_step"] = "Đang trích xuất với LlamaParse..."
        extraction_jobs[job_id]["progress"] = 20
        
        result = await extractor.extract_from_pdf(pdf_path, category)
        
        # Convert to dict
        structure_dict = result.to_dict()
        
        extraction_jobs[job_id]["current_step"] = "Đang dọn dẹp và xác thực kết quả..."
        extraction_jobs[job_id]["progress"] = 85
        
        # POST-PROCESSING: Clean and validate
        from app.extraction.cleaner import clean_extraction_result
        
        temp_result = {
            "source_file": pdf_path.name,
            "structure": structure_dict
        }
        cleaned_result, cleaning_stats = clean_extraction_result(temp_result)
        structure_dict = cleaned_result.get("structure", structure_dict)
        
        extraction_jobs[job_id]["progress"] = 90
        extraction_jobs[job_id]["current_step"] = f"Hybrid Stage 1 hoàn thành: {len(structure_dict.get('articles', []))} điều"
        
        # Save result
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_result = {
            "extraction_id": job_id,
            "stage": "stage1_hybrid",
            "extraction_mode": "llamaparse_vlm_hybrid",
            "source_file": pdf_path.name,
            "extracted_at": datetime.now().isoformat(),
            "category": category,
            "page_count": structure_dict.get("page_count", 0),
            "structure": structure_dict,
            "cleaning_applied": True,
            "document_type": "original" if cleaning_stats.is_original_document else "amendment",
            "cleaning_stats": {
                "duplicates_removed": cleaning_stats.duplicate_nodes_removed,
                "orphan_relations_removed": cleaning_stats.orphan_relations_removed,
                "invalid_modifications_removed": cleaning_stats.invalid_modifications_removed,
                "is_original_document": cleaning_stats.is_original_document,
                "issues_detected": len(cleaning_stats.errors),
                "issues": cleaning_stats.errors[:10] if cleaning_stats.errors else []
            }
        }
        
        result_file = RESULTS_DIR / f"stage1_hybrid_{timestamp}_{job_id[:8]}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(save_result, f, ensure_ascii=False, indent=2)
        
        # Complete
        extraction_jobs[job_id]["status"] = "completed"
        extraction_jobs[job_id]["progress"] = 100
        extraction_jobs[job_id]["current_step"] = "Hybrid Stage 1 hoàn thành!"
        extraction_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        extraction_jobs[job_id]["result_file"] = str(result_file.name)
        extraction_jobs[job_id]["stats"] = {
            "pages": structure_dict.get("page_count", 0),
            "chapters": len(structure_dict.get("chapters", [])),
            "articles": len(structure_dict.get("articles", [])),
            "clauses": len(structure_dict.get("clauses", [])),
            "tables": len(structure_dict.get("tables", [])),
            "extraction_mode": "hybrid_llamaparse_vlm",
            "duplicates_removed": cleaning_stats.duplicate_nodes_removed,
            "issues_detected": len(cleaning_stats.errors)
        }
        
    except Exception as e:
        import traceback
        extraction_jobs[job_id]["status"] = "failed"
        extraction_jobs[job_id]["error"] = str(e)
        extraction_jobs[job_id]["current_step"] = f"Lỗi: {str(e)}"
        logger.error(f"Hybrid Stage 1 extraction error: {traceback.format_exc()}")


@router.post("/stage1/hybrid/upload", response_model=ExtractionStatus)
@router.post("/stage1/upload", response_model=ExtractionStatus)  # Alias for backward compatibility
async def upload_and_extract_stage1_hybrid(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = "Quy chế Đào tạo"
):
    """
    Stage 1: Upload PDF and extract using LlamaParse + VLM (Hybrid Mode).
    
    This endpoint combines:
    - LlamaParse: For high-quality text and table extraction
    - VLM: For accurate structure boundary detection
    
    Benefits:
    - Better text quality than pure VLM
    - Better structure detection than pure LlamaParse
    - Lower API costs
    - Superior table handling
    
    Returns JSON with chapters, articles, clauses structure.
    
    Note: Both /stage1/upload and /stage1/hybrid/upload point to this endpoint.
    """
    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file PDF")
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save uploaded file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    pdf_path = UPLOAD_DIR / safe_filename
    
    try:
        with open(pdf_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lưu file: {str(e)}")
    
    # Initialize job status
    extraction_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "current_step": "Đang khởi tạo Hybrid Stage 1 (LlamaParse + VLM)...",
        "stage": "stage1_hybrid",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "result_file": None,
        "error": None,
        "stats": None
    }
    
    # Start hybrid extraction in background
    background_tasks.add_task(
        run_hybrid_stage1_pipeline,
        job_id,
        pdf_path,
        category
    )
    
    return ExtractionStatus(**extraction_jobs[job_id])


# =============================================================================
# Stage 2 Endpoint: LLM + Merge
# =============================================================================

@router.post("/stage2/process", response_model=ExtractionStatus)
async def process_stage2(
    background_tasks: BackgroundTasks,
    request: Stage2Request
):
    """
    Stage 2: Process Stage 1 JSON to extract semantic entities and relations.
    
    Input: JSON from Stage 1 (structure)
    Output: Merged JSON with structure + semantics
    """
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Initialize job status
    extraction_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "current_step": "Đang khởi tạo Stage 2...",
        "stage": "stage2",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "result_file": None,
        "error": None,
        "stats": None
    }
    
    # Start Stage 2 extraction in background
    background_tasks.add_task(
        run_stage2_pipeline,
        job_id,
        request.stage1_data,
        request.category,
        request.push_to_neo4j
    )
    
    return ExtractionStatus(**extraction_jobs[job_id])


@router.post("/stage2/upload", response_model=ExtractionStatus)
async def upload_stage1_json_and_process(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = "Quy chế Đào tạo",
    push_to_neo4j: bool = False
):
    """
    Stage 2: Upload Stage 1 JSON file and process with LLM.
    
    Alternative to /stage2/process - accepts file upload instead of JSON body.
    """
    # Validate file
    if not file.filename.lower().endswith('.json'):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file JSON")
    
    try:
        content = await file.read()
        stage1_data = json.loads(content.decode('utf-8'))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"File JSON không hợp lệ: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi đọc file: {str(e)}")
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Initialize job status
    extraction_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "current_step": "Đang khởi tạo Stage 2...",
        "stage": "stage2",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "result_file": None,
        "error": None,
        "stats": None
    }
    
    # Start Stage 2 extraction in background
    background_tasks.add_task(
        run_stage2_pipeline,
        job_id,
        stage1_data,
        category,
        push_to_neo4j
    )
    
    return ExtractionStatus(**extraction_jobs[job_id])


@router.get("/status/{job_id}", response_model=ExtractionStatus)
async def get_status(job_id: str):
    """Get the status of an extraction job."""
    status = get_extraction_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job không tồn tại")
    return status


@router.get("/result/{job_id}")
async def get_result(job_id: str):
    """Get the extraction result JSON."""
    status = get_extraction_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job không tồn tại")
    
    if status.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job chưa hoàn thành: {status.status}")
    
    result_path = RESULTS_DIR / status.result_file
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="File kết quả không tồn tại")
    
    with open(result_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@router.get("/download/{job_id}")
async def download_result(job_id: str):
    """Download the extraction result as JSON file."""
    status = get_extraction_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job không tồn tại")
    
    if status.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job chưa hoàn thành: {status.status}")
    
    result_path = RESULTS_DIR / status.result_file
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="File kết quả không tồn tại")
    
    return FileResponse(
        path=result_path,
        filename=status.result_file,
        media_type="application/json"
    )


@router.get("/jobs")
async def list_jobs():
    """List all extraction jobs."""
    return [ExtractionStatus(**job) for job in extraction_jobs.values()]


# =============================================================================
# Neo4j Import: Upload JSON and Push to Neo4j
# =============================================================================

class Neo4jImportRequest(BaseModel):
    """Request model for direct Neo4j import."""
    data: Dict[str, Any]


@router.post("/neo4j/upload")
async def upload_json_to_neo4j(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    clear_existing: bool = False
):
    """
    Upload a JSON file and push to Neo4j.
    
    Accepts extraction result JSON from Stage 1, Stage 2, or merged results.
    """
    # Validate file
    if not file.filename.lower().endswith('.json'):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file JSON")
    
    try:
        content = await file.read()
        data = json.loads(content.decode('utf-8'))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"File JSON không hợp lệ: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi đọc file: {str(e)}")
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Initialize job status
    extraction_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "current_step": "Đang chuẩn bị import Neo4j...",
        "stage": "neo4j_import",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "result_file": None,
        "error": None,
        "stats": None
    }
    
    # Start import in background
    background_tasks.add_task(
        run_neo4j_import,
        job_id,
        data,
        file.filename,
        clear_existing
    )
    
    return ExtractionStatus(**extraction_jobs[job_id])


async def run_neo4j_import(
    job_id: str,
    data: Dict[str, Any],
    filename: str,
    clear_existing: bool
):
    """
    Import extraction data to Neo4j.
    """
    try:
        extraction_jobs[job_id]["status"] = "processing"
        extraction_jobs[job_id]["current_step"] = "Đang kết nối Neo4j..."
        extraction_jobs[job_id]["progress"] = 10
        
        from app.ingest.indexing.graph_builder import Neo4jGraphBuilder
        
        uri = os.getenv("NEO4J_URI", "")
        user = os.getenv("NEO4J_USERNAME", "")
        password = os.getenv("NEO4J_PASSWORD", "")
        
        extraction_jobs[job_id]["progress"] = 20
        extraction_jobs[job_id]["current_step"] = "Đang xử lý dữ liệu..."
        
        # Get category from data
        category = data.get("category", "Quy chế Đào tạo")
        
        with Neo4jGraphBuilder(uri=uri, user=user, password=password) as builder:
            extraction_jobs[job_id]["progress"] = 30
            extraction_jobs[job_id]["current_step"] = "Đang import vào Neo4j..."
            
            # Use build_graph method which handles all the logic
            stats = builder.build_graph(
                extraction_data=data,
                category=category,
                clear_first=clear_existing
            )
            
            extraction_jobs[job_id]["progress"] = 90
            
            # Get final stats
            db_stats = builder.get_graph_stats()
        
        extraction_jobs[job_id]["progress"] = 100
        extraction_jobs[job_id]["status"] = "completed"
        extraction_jobs[job_id]["current_step"] = "Import Neo4j hoàn thành!"
        extraction_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        extraction_jobs[job_id]["stats"] = {
            "source_file": filename,
            "category": category,
            "imported": {
                "documents": stats.documents,
                "chapters": stats.chapters,
                "articles": stats.articles,
                "clauses": stats.clauses,
                "entities": stats.entities,
                "entities_merged": stats.entities_merged,
                "structural_relations": stats.structural_relations,
                "semantic_relations": stats.semantic_relations
            },
            "neo4j_stats": db_stats
        }
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Neo4j import error: {error_trace}")
        
        extraction_jobs[job_id]["status"] = "failed"
        extraction_jobs[job_id]["error"] = str(e)
        extraction_jobs[job_id]["current_step"] = f"Lỗi: {str(e)}"


@router.post("/neo4j/import")
async def import_json_to_neo4j(
    request: Neo4jImportRequest,
    background_tasks: BackgroundTasks,
    clear_existing: bool = False
):
    """
    Import JSON data directly to Neo4j (via request body instead of file upload).
    """
    job_id = str(uuid.uuid4())
    
    extraction_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "current_step": "Đang chuẩn bị import Neo4j...",
        "stage": "neo4j_import",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "result_file": None,
        "error": None,
        "stats": None
    }
    
    background_tasks.add_task(
        run_neo4j_import,
        job_id,
        request.data,
        "api_request",
        clear_existing
    )
    
    return ExtractionStatus(**extraction_jobs[job_id])


@router.get("/neo4j/stats")
async def get_neo4j_stats():
    """Get current Neo4j database statistics."""
    try:
        from app.ingest.indexing.graph_builder import Neo4jGraphBuilder
        
        uri = os.getenv("NEO4J_URI", "")
        user = os.getenv("NEO4J_USERNAME", "")
        password = os.getenv("NEO4J_PASSWORD", "")
        
        with Neo4jGraphBuilder(uri=uri, user=user, password=password) as builder:
            stats = builder.get_graph_stats()
        
        return {"status": "connected", "stats": stats}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.delete("/neo4j/clear")
async def clear_neo4j():
    """Clear all data from Neo4j database."""
    try:
        from app.ingest.indexing.graph_builder import Neo4jGraphBuilder
        
        uri = os.getenv("NEO4J_URI", "")
        user = os.getenv("NEO4J_USERNAME", "")
        password = os.getenv("NEO4J_PASSWORD", "")
        
        with Neo4jGraphBuilder(uri=uri, user=user, password=password) as builder:
            builder.clear_database()
        
        return {"status": "success", "message": "Đã xóa toàn bộ dữ liệu Neo4j"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# VECTOR DATABASE (Qdrant) INDEXING
# =============================================================================

@router.post("/vector/upload")
async def upload_json_to_qdrant(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: str = "regulation"
):
    """
    Upload a JSON file and index to Qdrant vector database.
    """
    if not file.filename.lower().endswith('.json'):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file JSON")
    
    try:
        content = await file.read()
        data = json.loads(content.decode('utf-8'))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"File JSON không hợp lệ: {str(e)}")
    
    job_id = str(uuid.uuid4())
    
    extraction_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "current_step": "Đang chuẩn bị index Qdrant...",
        "stage": "qdrant_index",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "result_file": None,
        "error": None,
        "stats": None
    }
    
    background_tasks.add_task(
        run_qdrant_index,
        job_id,
        data,
        file.filename,
        doc_type
    )
    
    return ExtractionStatus(**extraction_jobs[job_id])


async def run_qdrant_index(
    job_id: str,
    data: Dict[str, Any],
    filename: str,
    doc_type: str
):
    """Index extraction data to Qdrant."""
    try:
        extraction_jobs[job_id]["status"] = "processing"
        extraction_jobs[job_id]["current_step"] = "Đang xử lý dữ liệu JSON..."
        extraction_jobs[job_id]["progress"] = 10
        
        from app.ingest.indexing.index_semantic_data import load_and_process_json, convert_to_document_chunks
        from app.search.adapters.qdrant_vector_adapter import QdrantVectorAdapter
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        from app.shared.config.settings import settings
        import tempfile
        
        # Save data to temp file for processing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
            temp_path = f.name
        
        extraction_jobs[job_id]["progress"] = 20
        extraction_jobs[job_id]["current_step"] = "Đang trích xuất chunks..."
        
        # Process JSON to chunks
        chunks_data = load_and_process_json(temp_path, doc_type)
        
        if not chunks_data:
            raise Exception("Không thể trích xuất chunks từ JSON")
        
        extraction_jobs[job_id]["progress"] = 40
        extraction_jobs[job_id]["current_step"] = f"Đang chuyển đổi {len(chunks_data)} chunks..."
        
        # Convert to DocumentChunk
        doc_filename = Path(filename).stem
        document_chunks = convert_to_document_chunks(chunks_data, doc_filename)
        
        extraction_jobs[job_id]["progress"] = 50
        extraction_jobs[job_id]["current_step"] = "Đang kết nối Qdrant..."
        
        # Initialize embedding model and adapter
        embedding_model = HuggingFaceEmbedding(model_name=settings.emb_model)
        qdrant_url = os.getenv("QDRANT_URL", settings.qdrant_url)
        qdrant_api_key = os.getenv("QDRANT_API_KEY", settings.qdrant_api_key)
        
        vector_adapter = QdrantVectorAdapter(
            qdrant_url=qdrant_url,
            embedding_model=embedding_model,
            api_key=qdrant_api_key or None
        )
        
        extraction_jobs[job_id]["progress"] = 60
        extraction_jobs[job_id]["current_step"] = f"Đang index {len(document_chunks)} documents..."
        
        # Index in batches
        batch_size = 50
        total = len(document_chunks)
        indexed = 0
        
        for i in range(0, total, batch_size):
            batch = document_chunks[i:i + batch_size]
            success = await vector_adapter.index_documents(batch)
            if success:
                indexed += len(batch)
            progress = 60 + int((i / total) * 30)
            extraction_jobs[job_id]["progress"] = progress
            extraction_jobs[job_id]["current_step"] = f"Đã index {indexed}/{total} documents..."
        
        # Cleanup temp file
        os.unlink(temp_path)
        
        extraction_jobs[job_id]["progress"] = 100
        extraction_jobs[job_id]["status"] = "completed"
        extraction_jobs[job_id]["current_step"] = "Index Qdrant hoàn thành!"
        extraction_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        extraction_jobs[job_id]["stats"] = {
            "source_file": filename,
            "doc_type": doc_type,
            "chunks_processed": len(chunks_data),
            "documents_indexed": indexed,
            "embedding_model": settings.emb_model
        }
        
    except Exception as e:
        import traceback
        print(f"Qdrant index error: {traceback.format_exc()}")
        extraction_jobs[job_id]["status"] = "failed"
        extraction_jobs[job_id]["error"] = str(e)
        extraction_jobs[job_id]["current_step"] = f"Lỗi: {str(e)}"


@router.get("/vector/stats")
async def get_vector_stats():
    """Get Qdrant vector database statistics."""
    try:
        from app.ingest.store.vector.qdrant_store import get_qdrant_client, get_collection_name
        
        client = get_qdrant_client()
        collection_name = get_collection_name()
        info = client.get_collection(collection_name)
        
        return {
            "status": "connected",
            "stats": {
                "collection": collection_name,
                "total_documents": info.points_count,
                "vectors_count": info.vectors_count,
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# =============================================================================
# OPENSEARCH (BM25) INDEXING
# =============================================================================

@router.post("/opensearch/upload")
async def upload_json_to_opensearch(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: str = "regulation",
    clear_existing: bool = False
):
    """
    Upload a JSON file and index to OpenSearch (BM25 keyword search).
    """
    if not file.filename.lower().endswith('.json'):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file JSON")
    
    try:
        content = await file.read()
        data = json.loads(content.decode('utf-8'))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"File JSON không hợp lệ: {str(e)}")
    
    job_id = str(uuid.uuid4())
    
    extraction_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "current_step": "Đang chuẩn bị index OpenSearch...",
        "stage": "opensearch_index",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "result_file": None,
        "error": None,
        "stats": None
    }
    
    background_tasks.add_task(
        run_opensearch_index,
        job_id,
        data,
        file.filename,
        doc_type,
        clear_existing
    )
    
    return ExtractionStatus(**extraction_jobs[job_id])


async def run_opensearch_index(
    job_id: str,
    data: Dict[str, Any],
    filename: str,
    doc_type: str,
    clear_existing: bool
):
    """Index extraction data to OpenSearch."""
    try:
        extraction_jobs[job_id]["status"] = "processing"
        extraction_jobs[job_id]["current_step"] = "Đang xử lý dữ liệu JSON..."
        extraction_jobs[job_id]["progress"] = 10
        
        from app.ingest.indexing.index_opensearch_data import load_and_process_json, convert_to_opensearch_documents
        from app.ingest.store.opensearch.client import OpenSearchClient
        import tempfile
        
        # Save data to temp file for processing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
            temp_path = f.name
        
        extraction_jobs[job_id]["progress"] = 20
        extraction_jobs[job_id]["current_step"] = "Đang trích xuất chunks..."
        
        # Process JSON to chunks
        chunks_data = load_and_process_json(temp_path, doc_type)
        
        if not chunks_data:
            raise Exception("Không thể trích xuất chunks từ JSON")
        
        extraction_jobs[job_id]["progress"] = 40
        extraction_jobs[job_id]["current_step"] = f"Đang chuyển đổi {len(chunks_data)} chunks..."
        
        # Convert to OpenSearch documents
        doc_filename = Path(filename).stem
        documents = convert_to_opensearch_documents(chunks_data, doc_filename)
        
        extraction_jobs[job_id]["progress"] = 50
        extraction_jobs[job_id]["current_step"] = "Đang kết nối OpenSearch..."
        
        # Initialize OpenSearch client
        client = OpenSearchClient()
        
        # Clear existing if requested
        if clear_existing:
            extraction_jobs[job_id]["current_step"] = "Đang xóa dữ liệu cũ..."
            try:
                delete_result = client.client.delete_by_query(
                    index=client.index_name,
                    body={"query": {"term": {"doc_id": doc_filename}}}
                )
                deleted = delete_result.get("deleted", 0)
                print(f"Deleted {deleted} existing documents")
            except Exception as e:
                print(f"Warning: Could not clear existing: {e}")
        
        extraction_jobs[job_id]["progress"] = 60
        extraction_jobs[job_id]["current_step"] = f"Đang index {len(documents)} documents..."
        
        # Index in batches
        batch_size = 100
        total = len(documents)
        total_success = 0
        total_failed = 0
        
        for i in range(0, total, batch_size):
            batch = documents[i:i + batch_size]
            try:
                success, failed = client.bulk_index_documents(batch)
                total_success += success
                total_failed += failed
            except Exception as e:
                total_failed += len(batch)
                print(f"Batch error: {e}")
            
            progress = 60 + int((i / total) * 30)
            extraction_jobs[job_id]["progress"] = progress
            extraction_jobs[job_id]["current_step"] = f"Đã index {total_success}/{total} documents..."
        
        # Cleanup temp file
        os.unlink(temp_path)
        
        extraction_jobs[job_id]["progress"] = 100
        extraction_jobs[job_id]["status"] = "completed"
        extraction_jobs[job_id]["current_step"] = "Index OpenSearch hoàn thành!"
        extraction_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        extraction_jobs[job_id]["stats"] = {
            "source_file": filename,
            "doc_type": doc_type,
            "chunks_processed": len(chunks_data),
            "documents_indexed": total_success,
            "documents_failed": total_failed,
            "index_name": client.index_name
        }
        
    except Exception as e:
        import traceback
        print(f"OpenSearch index error: {traceback.format_exc()}")
        extraction_jobs[job_id]["status"] = "failed"
        extraction_jobs[job_id]["error"] = str(e)
        extraction_jobs[job_id]["current_step"] = f"Lỗi: {str(e)}"


@router.get("/opensearch/stats")
async def get_opensearch_stats():
    """Get OpenSearch index statistics."""
    try:
        from app.ingest.store.opensearch.client import OpenSearchClient
        
        client = OpenSearchClient()
        
        # Get index stats
        stats = client.client.indices.stats(index=client.index_name)
        doc_count = stats['indices'][client.index_name]['primaries']['docs']['count']
        
        return {
            "status": "connected",
            "stats": {
                "index_name": client.index_name,
                "total_documents": doc_count
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}