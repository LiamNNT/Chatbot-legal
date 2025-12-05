"""
API Routes for Knowledge Graph Extraction Pipeline.

Provides endpoints for:
- Upload PDF and extract knowledge graph (Two-Stage VLM + LLM)
- Get extraction status
- Download extraction results
"""

import os
import json
import asyncio
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

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


class ExtractionStatus(BaseModel):
    """Status of an extraction job."""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    current_step: str
    created_at: str
    completed_at: Optional[str] = None
    result_file: Optional[str] = None
    error: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None


def get_extraction_status(job_id: str) -> Optional[ExtractionStatus]:
    """Get status of an extraction job."""
    if job_id not in extraction_jobs:
        return None
    return ExtractionStatus(**extraction_jobs[job_id])


async def run_extraction_pipeline(
    job_id: str,
    pdf_path: Path,
    category: str,
    push_to_neo4j: bool
):
    """
    Run the Two-Stage extraction pipeline asynchronously.
    
    Stage 1: VLM for structural extraction (Document -> Articles -> Clauses)
    Stage 2: LLM for semantic extraction (Entities + Relations)
    """
    try:
        # Update status
        extraction_jobs[job_id]["status"] = "processing"
        extraction_jobs[job_id]["current_step"] = "Đang chuyển PDF sang ảnh..."
        extraction_jobs[job_id]["progress"] = 10
        
        # Import extraction modules
        import sys
        sys.path.insert(0, str(SCRIPTS_DIR))
        
        from hybrid_extractor import StructureExtractor, SemanticExtractor, VLMConfig, LLMConfig
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
        
        # Convert Pydantic model to dict if needed
        if hasattr(structure_result, 'model_dump'):
            structure_dict = structure_result.model_dump()
        else:
            structure_dict = structure_result
        
        extraction_jobs[job_id]["progress"] = 50
        extraction_jobs[job_id]["current_step"] = f"Stage 1 hoàn thành: {len(structure_dict.get('articles', []))} điều"
        
        # Stage 2: LLM Semantic Extraction  
        extraction_jobs[job_id]["current_step"] = "Stage 2: Trích xuất ngữ nghĩa với LLM..."
        extraction_jobs[job_id]["progress"] = 60
        
        # Extract semantics from each article
        all_entities = []
        all_relations = []
        errors = []
        
        articles = structure_dict.get('articles', [])
        for i, article in enumerate(articles):
            try:
                article_result = await loop.run_in_executor(
                    None,
                    lambda a=article: semantic_extractor.extract_from_article(
                        article_id=a.get('id', ''),
                        article_title=a.get('title', ''),
                        article_text=a.get('full_text', '')
                    )
                )
                
                if hasattr(article_result, 'model_dump'):
                    article_dict = article_result.model_dump()
                else:
                    article_dict = article_result if isinstance(article_result, dict) else {}
                
                # Add entities and relations
                for entity in article_dict.get('nodes', []):
                    entity['source_article_id'] = article.get('id', '')
                    all_entities.append(entity)
                
                for rel in article_dict.get('edges', []):
                    rel['source_article_id'] = article.get('id', '')
                    all_relations.append(rel)
                    
            except Exception as e:
                errors.append({"article_id": article.get('id', ''), "error": str(e)})
            
            # Update progress
            progress = 60 + int(20 * (i + 1) / len(articles)) if articles else 80
            extraction_jobs[job_id]["progress"] = progress
        
        semantic_result = {
            "entities": all_entities,
            "relations": all_relations,
            "errors": errors,
            "stats": {
                "entities": len(all_entities),
                "relations": len(all_relations),
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
        
        # Push to Neo4j if requested
        if push_to_neo4j:
            extraction_jobs[job_id]["current_step"] = "Đang đẩy dữ liệu lên Neo4j..."
            try:
                from graph_builder import Neo4jGraphBuilder
                
                uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
                user = os.getenv("NEO4J_USER", "neo4j")
                password = os.getenv("NEO4J_PASSWORD", "password")
                
                with Neo4jGraphBuilder(uri=uri, user=user, password=password) as builder:
                    stats = builder.build_graph(
                        extraction_data=result,
                        category=category,
                        clear_first=False
                    )
                    extraction_jobs[job_id]["stats"]["neo4j"] = {
                        "entities": stats.entities,
                        "merged": stats.entities_merged,
                        "relations": stats.semantic_relations
                    }
            except Exception as e:
                extraction_jobs[job_id]["stats"]["neo4j_error"] = str(e)
        
        # Complete
        extraction_jobs[job_id]["status"] = "completed"
        extraction_jobs[job_id]["progress"] = 100
        extraction_jobs[job_id]["current_step"] = "Hoàn thành!"
        extraction_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        extraction_jobs[job_id]["result_file"] = str(result_file.name)
        extraction_jobs[job_id]["stats"] = {
            "pages": len(pages),
            "articles": len(structure_dict.get("articles", [])),
            "clauses": len(structure_dict.get("clauses", [])),
            "entities": semantic_result.get("stats", {}).get("entities", 0),
            "relations": semantic_result.get("stats", {}).get("relations", 0)
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
