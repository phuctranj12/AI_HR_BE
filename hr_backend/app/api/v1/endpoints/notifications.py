from datetime import date, timedelta
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor

from app.api.v1.deps import get_db

router = APIRouter(prefix="/notifications", tags=["notifications"])

REQUIRED_DOCS = {"CCCD", "Ly_lich", "Giay_kham_suc_khoe"}

class MissingDocEmployee(BaseModel):
    employee_id: int
    employee_code: Optional[str]
    full_name: str
    folder_path: str
    missing_docs: List[str]

class ExpiredDocumentInfo(BaseModel):
    employee_id: int
    employee_code: Optional[str]
    full_name: str
    folder_path: str
    document_id: int
    document_name: str
    doc_type: str
    end_date: date

@router.get("/missing-documents", response_model=List[MissingDocEmployee])
def get_missing_documents(db: Any = Depends(get_db)):
    """
    Returns a list of active employees who are missing core required documents
    or have missing mandatory metadata.
    """
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT e.id, e.employee_code, e.full_name, e.folder_path,
                   array_agg(dt.type_name) as existing_docs
            FROM employees e
            JOIN statuses s ON e.status_id = s.id
            LEFT JOIN documents d ON e.id = d.employee_id
            LEFT JOIN document_types dt ON d.document_type_id = dt.id
            WHERE s.status_name = 'Active'
            GROUP BY e.id
            """
        )
        rows = cur.fetchall()

    results = []
    for row in rows:
        existing = set(row["existing_docs"]) if row["existing_docs"] and row["existing_docs"][0] is not None else set()
        
        # Normalize types because document_types might have variations like CCCD_1
        normalized_existing = {d.upper() for d in existing}
        
        missing = []
        for req in REQUIRED_DOCS:
            req_upper = req.upper()
            if req_upper not in normalized_existing and not any(r.startswith(req_upper) for r in normalized_existing):
                missing.append(req)

        if missing:
            results.append(MissingDocEmployee(
                employee_id=row["id"],
                employee_code=row["employee_code"],
                full_name=row["full_name"],
                folder_path=row["folder_path"],
                missing_docs=missing
            ))

    return results

@router.get("/expired-documents", response_model=List[ExpiredDocumentInfo])
def get_expired_documents(days: int = 30, db: Any = Depends(get_db)):
    """
    Returns active employees' documents that are expired or expiring within `days` ahead.
    """
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT e.id as employee_id, e.employee_code, e.full_name, e.folder_path,
                   d.id as document_id, d.document_name, d.end_date, dt.type_name as doc_type
            FROM documents d
            JOIN employees e ON d.employee_id = e.id
            JOIN statuses s ON e.status_id = s.id
            JOIN document_types dt ON d.document_type_id = dt.id
            WHERE s.status_name = 'Active'
              AND d.end_date IS NOT NULL 
              AND d.end_date <= CURRENT_DATE + (%s * interval '1 day')
            ORDER BY d.end_date ASC
            """,
            (days,)
        )
        rows = cur.fetchall()

    return [ExpiredDocumentInfo(**row) for row in rows]
