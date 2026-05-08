from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers.analysis import router as analysis_router
from app.routers.upload import router as upload_router

settings = get_settings()

app = FastAPI(
    title="ReqSmell Backend",
    description="FastAPI backend for GenAI-powered requirements smell detection.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(upload_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
