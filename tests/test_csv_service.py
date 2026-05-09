from __future__ import annotations

from fastapi import HTTPException

from app.services.csv_service import parse_csv_text


def test_parse_csv_text_detects_columns_and_rows() -> None:
    result = parse_csv_text(
        "req_id,requirement_text,domain,type,project\n"
        "REQ-1,The system shall respond quickly,Auth,NFR,Portal\n",
        "requirements.csv",
        64,
    )

    assert result.file.rowCount == 1
    assert result.requirements[0].id == "REQ-1"
    assert result.requirements[0].text == "The system shall respond quickly"
    assert result.detectedColumns == ["id", "text", "domain", "type", "project"]


def test_parse_csv_text_requires_text_column() -> None:
    try:
        parse_csv_text("id,domain\nREQ-1,Auth\n", "bad.csv", 24)
    except HTTPException as error:
        assert error.status_code == 422
    else:
        raise AssertionError("Expected HTTPException for CSV without text column.")
