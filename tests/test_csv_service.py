"""Tests for the CSV upload and parsing service."""

from __future__ import annotations

from fastapi import HTTPException

from app.services.csv_service import parse_csv_text


def test_parse_csv_text_detects_columns_and_rows() -> None:
    """Verify that all five standard columns are detected and one row is parsed."""
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


def test_parse_csv_text_detects_group_id_as_project() -> None:
    """Verify that group_id style headers map to the project field."""
    result = parse_csv_text(
        "id,text,group_id\nREQ-1,The system shall respond quickly,Portal\n",
        "requirements.csv",
        64,
    )

    assert result.detection.project is True
    assert result.requirements[0].project == "Portal"


def test_parse_csv_text_rejects_duplicate_requirement_ids() -> None:
    """Verify that duplicate requirement IDs are rejected before analysis starts."""
    try:
        parse_csv_text(
            "id,text\nREQ-1,The system shall respond quickly\nREQ-1,The system shall export CSV\n",
            "requirements.csv",
            96,
        )
    except HTTPException as error:
        assert error.status_code == 422
        assert "Duplicate ID(s): REQ-1" in str(error.detail)
    else:
        raise AssertionError("Expected HTTPException for duplicate requirement IDs.")


def test_parse_csv_text_requires_text_column() -> None:
    """Verify that a CSV missing a text column raises HTTP 422."""
    try:
        parse_csv_text("id,domain\nREQ-1,Auth\n", "bad.csv", 24)
    except HTTPException as error:
        assert error.status_code == 422
    else:
        raise AssertionError("Expected HTTPException for CSV without text column.")
