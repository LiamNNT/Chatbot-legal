from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.embed import router as embed_router
from app.api.v1.routes.search import router as search_router
from app.api.v1.routes.admin import router as admin_router

app = FastAPI(title="RAG Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/v1")
app.include_router(embed_router, prefix="/v1")
app.include_router(search_router, prefix="/v1")
app.include_router(admin_router, prefix="/v1")

@app.get("/")
def root():
    return {"service": "rag", "env": settings.app_env}