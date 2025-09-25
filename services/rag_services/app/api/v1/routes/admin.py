from fastapi import APIRouter, HTTPException
from app.api.schemas.doc import ManifestSpec, ReindexResponse
from indexing.pipeline import reindex_from_manifest

router = APIRouter(tags=["admin"])

@router.post("/admin/reindex", response_model=ReindexResponse)
def reindex(manifest: ManifestSpec):
    if not manifest.source_dir:
        raise HTTPException(status_code=400, detail="source_dir is required")
    count = reindex_from_manifest(manifest)
    return ReindexResponse(status="ok", indexed_docs=count)
