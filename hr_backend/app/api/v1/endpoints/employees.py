import logging

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.api.v1.deps import DbDep
from app.db.employee_repo import create_employee, delete_employee, get_employee, list_employees, update_employee

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", summary="List employees")
def get_employees(
    db: DbDep,
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    return {"employees": list_employees(db, q=q, limit=limit)}


@router.get("/{employee_id}", summary="Get an employee")
def get_employee_by_id(employee_id: int, db: DbDep) -> dict:
    try:
        return get_employee(db, employee_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("", summary="Create employee", status_code=status.HTTP_201_CREATED)
def post_employee(body: dict, db: DbDep) -> dict:
    if not (body.get("full_name") or "").strip():
        raise HTTPException(status_code=422, detail="full_name is required")
    try:
        return create_employee(db, body)
    except Exception as exc:
        logger.exception("create_employee failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.patch("/{employee_id}", summary="Update employee")
def patch_employee(employee_id: int, body: dict, db: DbDep) -> dict:
    try:
        return update_employee(db, employee_id, body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("update_employee failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{employee_id}", summary="Delete employee", status_code=status.HTTP_200_OK)
def del_employee(employee_id: int, db: DbDep) -> dict:
    try:
        delete_employee(db, employee_id)
        return {"deleted": employee_id}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("delete_employee failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

