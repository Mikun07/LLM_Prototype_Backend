from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from app.models import UploadResponse
from app.services.csv_service import parse_upload

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", response_model=UploadResponse)
async def upload_csv(file: Annotated[UploadFile, File(...)]) -> UploadResponse:
    """Accept a CSV upload, parse it, and return requirements with column metadata."""
    return await parse_upload(file)
