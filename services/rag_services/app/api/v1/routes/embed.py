from fastapi import APIRouter, HTTPException
from app.api.schemas.embed import EmbedRequest, EmbedResponse
from app.config.settings import settings
from sentence_transformers import SentenceTransformer

router = APIRouter(tags=["embed"])
_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.emb_model)
    return _model

@router.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest):
    if len(req.texts) > 64:
        raise HTTPException(status_code=400, detail="Max 64 texts per request for demo.")
    model = get_model()
    vectors = model.encode(req.texts, normalize_embeddings=True).tolist()
    return EmbedResponse(vectors=vectors)
