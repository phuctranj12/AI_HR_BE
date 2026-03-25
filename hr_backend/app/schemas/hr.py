from pathlib import Path

from pydantic import BaseModel, Field
from typing import Optional

from app.models.document import DocType


# ── Gemini analysis ──────────────────────────────────────────────────────────

class DocumentInfo(BaseModel):
    person_name: Optional[str] = Field(None, description="Full name of the document owner")
    doc_type: str = Field("Khac", description="Classified document type")


# ── Processing results ───────────────────────────────────────────────────────

class FileProcessResult(BaseModel):
    original_filename: str
    person_name: Optional[str]
    doc_type: str
    destination: str
    status: str = "ok"
    error: Optional[str] = None


class ProcessDocumentsResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: list[FileProcessResult]


# ── Face matching results ────────────────────────────────────────────────────

class FaceMatchResult(BaseModel):
    photo_filename: str
    matched_person: Optional[str]
    distance: Optional[float]
    destination: str
    status: str = "ok"
    error: Optional[str] = None


class MatchFacesResponse(BaseModel):
    anchors_built: int
    photos_processed: int
    results: list[FaceMatchResult]


# ── Storage listing ──────────────────────────────────────────────────────────

class PersonFolder(BaseModel):
    name: str
    display_name: Optional[str] = None
    files: list[str]


class OutputListResponse(BaseModel):
    persons: list[PersonFolder]
