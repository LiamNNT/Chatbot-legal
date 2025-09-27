# app/api/v1/routes/admin.py
#
# Description:
# This module implements administrative endpoints for the RAG service.
# It currently includes the endpoint for triggering the document re-indexing process.

from fastapi import APIRouter, HTTPException
from app.api.schemas.doc import ManifestSpec, ReindexResponse
from indexing.pipeline import reindex_from_manifest

# Create an API router for admin-related endpoints
router = APIRouter(tags=["admin"])

@router.post("/admin/reindex", response_model=ReindexResponse)
def reindex(manifest: ManifestSpec):
    """
    Endpoint to trigger the re-indexing of documents from a specified source directory.

    Args:
        manifest (ManifestSpec): The manifest detailing the source and configuration for indexing.

    Returns:
        ReindexResponse: The status and count of indexed documents.
    """
    if not manifest.source_dir:
        raise HTTPException(status_code=400, detail="source_dir is required")
    
    # Delegate the indexing logic to the pipeline module
    count = reindex_from_manifest(manifest)
    
    return ReindexResponse(status="ok", indexed_docs=count)