from pathlib import Path

from pydantic import BaseModel, Field
from typing import Optional

from app.models.document import DocType


# ── Gemini analysis ──────────────────────────────────────────────────────────

class DocumentInfo(BaseModel):
    person_name: Optional[str] = Field(None, description="Full name of the document owner")
    doc_type: str = Field("Khac", description="Classified document type")
    
    # Newly extracted employee fields
    employee_code: Optional[str] = None
    date_of_birth: Optional[str] = None
    hometown: Optional[str] = None
    join_date: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    permanent_address: Optional[str] = None
    position: Optional[str] = None
    
    # Newly extracted document fields
    issued_date: Optional[str] = None
    issued_by: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    document_number: Optional[str] = None


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
