import logging

from fastapi import APIRouter, HTTPException, status

from app.api.v1.deps import DbDep
from app.db.catalog_repo import (
    create_document_type,
    delete_document_type,
    list_document_types,
    list_statuses,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/document-types", summary="List document types")
def get_document_types(db: DbDep) -> dict:
    return {"document_types": list_document_types(db)}


@router.post("/document-types", summary="Create a document type", status_code=status.HTTP_201_CREATED)
def post_document_type(body: dict, db: DbDep) -> dict:
    name = (body.get("type_name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="type_name is required")
    try:
        return create_document_type(db, name)
    except Exception as exc:
        logger.exception("create_document_type failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/document-types/{doc_type_id}", summary="Delete a document type")
def del_document_type(doc_type_id: int, db: DbDep) -> dict:
    try:
        delete_document_type(db, doc_type_id)
        return {"deleted": doc_type_id}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("delete_document_type failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/statuses", summary="List statuses")
def get_statuses(db: DbDep) -> dict:
    return {"statuses": list_statuses(db)}

