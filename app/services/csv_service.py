from __future__ import annotations

import csv
import re
from collections.abc import Iterable, Sequence
from io import StringIO

from fastapi import HTTPException, UploadFile, status

from app.config import Settings, get_settings
from app.models import ColumnDetection, FileMetadata, RequirementRow, UploadResponse

ColumnKey = str

COLUMN_ALIASES: dict[ColumnKey, tuple[str, ...]] = {
    "id": ("id", "req id", "req_id", "requirement id", "requirement_id", "reqid"),
    "text": (
        "text",
        "requirement",
        "description",
        "requirement text",
        "requirement_text",
    ),
    "domain": ("domain", "area", "module"),
    "type": ("type", "requirement type", "requirement_type"),
    "project": ("project", "system", "product", "project name", "project_name"),
}


def normalise_header(value: str) -> str:
    cleaned = value.strip().lower().replace("_", " ")
    return re.sub(r"\s+", " ", cleaned)


def find_column(headers: Iterable[str], key: ColumnKey) -> str | None:
    aliases = COLUMN_ALIASES[key]
    return next((header for header in headers if normalise_header(header) in aliases), None)


def detect_columns(headers: Sequence[str]) -> ColumnDetection:
    return ColumnDetection(
        id=find_column(headers, "id") is not None,
        text=find_column(headers, "text") is not None,
        domain=find_column(headers, "domain") is not None,
        type=find_column(headers, "type") is not None,
        project=find_column(headers, "project") is not None,
    )


def read_value(row: dict[str, str | None], column: str | None) -> str:
    if column is None:
        return ""

    return (row.get(column) or "").strip()


def normalise_requirement_type(value: str) -> str:
    upper = value.strip().upper()
    if upper in {"FR", "FUNCTIONAL"}:
        return "FR"
    if upper in {"NFR", "NON-FUNCTIONAL", "NONFUNCTIONAL"}:
        return "NFR"

    return value.strip() or "UNKNOWN"


def has_csv_shape(file: UploadFile) -> bool:
    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()
    return (
        filename.endswith(".csv")
        or content_type == "text/csv"
        or content_type == "application/vnd.ms-excel"
    )


def parse_csv_text(text: str, file_name: str, file_size: int) -> UploadResponse:
    reader = csv.DictReader(StringIO(text))
    headers = reader.fieldnames or []
    detection = detect_columns(headers)
    text_column = find_column(headers, "text")

    if not headers or text_column is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "The CSV must include a text, requirement, description, "
                "or requirement_text column."
            ),
        )

    id_column = find_column(headers, "id")
    domain_column = find_column(headers, "domain")
    type_column = find_column(headers, "type")
    project_column = find_column(headers, "project")

    requirements: list[RequirementRow] = []
    for index, row in enumerate(reader, start=1):
        requirement_text = read_value(row, text_column)
        if requirement_text == "":
            continue

        requirements.append(
            RequirementRow(
                id=read_value(row, id_column) or f"REQ-{index:03d}",
                text=requirement_text,
                domain=read_value(row, domain_column) or "General",
                type=normalise_requirement_type(read_value(row, type_column)),
                project=read_value(row, project_column) or "Default",
            ),
        )

    if not requirements:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The CSV has headers but no requirement rows with text.",
        )

    detected_columns = [
        key for key, is_present in detection.model_dump().items() if bool(is_present)
    ]

    return UploadResponse(
        file=FileMetadata(name=file_name, size=file_size, rowCount=len(requirements)),
        requirements=requirements,
        detectedColumns=detected_columns,
        detection=detection,
    )


async def parse_upload(file: UploadFile, settings: Settings | None = None) -> UploadResponse:
    active_settings = settings or get_settings()
    if not has_csv_shape(file):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Upload a CSV file with a .csv extension.",
        )

    data = await file.read()
    max_size = active_settings.max_csv_size_mb * 1024 * 1024
    if len(data) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"CSV file exceeds the {active_settings.max_csv_size_mb} MB limit.",
        )

    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The selected CSV must be UTF-8 encoded.",
        ) from exc

    return parse_csv_text(text, file.filename or "requirements.csv", len(data))
