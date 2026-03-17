import logging

from fastapi import APIRouter, HTTPException, status

from app.api.v1.deps import DbDep
from app.db.project_repo import (
    add_project_member,
    create_project,
    delete_project,
    list_project_members,
    list_project_requirements,
    list_projects,
    remove_project_member,
    set_project_requirements,
    update_project,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", summary="List projects")
def get_projects(db: DbDep) -> dict:
    return {"projects": list_projects(db)}


@router.post("", summary="Create a project", status_code=status.HTTP_201_CREATED)
def post_project(body: dict, db: DbDep) -> dict:
    try:
        return create_project(db, body)
    except Exception as exc:
        logger.exception("create_project failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.patch("/{project_id}", summary="Update a project")
def patch_project(project_id: int, body: dict, db: DbDep) -> dict:
    try:
        return update_project(db, project_id, body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("update_project failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{project_id}", summary="Delete a project", status_code=status.HTTP_200_OK)
def del_project(project_id: int, db: DbDep) -> dict:
    try:
        delete_project(db, project_id)
        return {"deleted": project_id}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("delete_project failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{project_id}/members", summary="List project members")
def get_members(project_id: int, db: DbDep) -> dict:
    return {"members": list_project_members(db, project_id)}


@router.post("/{project_id}/members", summary="Add/Update a project member")
def post_member(project_id: int, body: dict, db: DbDep) -> dict:
    try:
        add_project_member(
            db,
            project_id=project_id,
            employee_id=int(body["employee_id"]),
            role=body.get("role"),
            start_date=body.get("start_date"),
            end_date=body.get("end_date"),
        )
        return {"ok": True}
    except KeyError:
        raise HTTPException(status_code=422, detail="employee_id is required")
    except Exception as exc:
        logger.exception("add_project_member failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{project_id}/members/{employee_id}", summary="Remove a project member")
def delete_member(project_id: int, employee_id: int, db: DbDep) -> dict:
    try:
        remove_project_member(db, project_id=project_id, employee_id=employee_id)
        return {"ok": True}
    except Exception as exc:
        logger.exception("remove_project_member failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{project_id}/requirements", summary="List required document types for project")
def get_requirements(project_id: int, db: DbDep) -> dict:
    return {"requirements": list_project_requirements(db, project_id)}


@router.put("/{project_id}/requirements", summary="Set required document types for project")
def put_requirements(project_id: int, body: dict, db: DbDep) -> dict:
    ids = body.get("document_type_ids")
    if not isinstance(ids, list):
        raise HTTPException(status_code=422, detail="document_type_ids must be a list[int]")
    try:
        set_project_requirements(db, project_id, [int(x) for x in ids])
        return {"ok": True}
    except Exception as exc:
        logger.exception("set_project_requirements failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

