import logging

from fastapi import APIRouter, HTTPException, status

from app.api.v1.deps import DbDep
from app.db.project_repo import (
    add_project_member,
    add_project_members_batch,
    create_project,
    delete_project,
    get_project,
    list_project_members,
    list_project_requirements,
    list_projects,
    remove_project_member,
    set_project_requirements,
    update_project,
    update_project_tree,
)
from app.schemas.projects import (
    ProjectCreate,
    ProjectEmployeeBatchCreate,
    ProjectEmployeeCreate,
    ProjectEmployeeList,
    ProjectList,
    ProjectOut,
    ProjectRequirementList,
    ProjectRequirementUpdate,
    ProjectTreeUpdate,
    ProjectUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", summary="List projects", response_model=ProjectList)
def get_projects(db: DbDep):
    return {"projects": list_projects(db)}


@router.post("", summary="Create a project", status_code=status.HTTP_201_CREATED, response_model=ProjectOut)
def post_project(body: ProjectCreate, db: DbDep):
    try:
        return create_project(db, body.model_dump())
    except Exception as exc:
        logger.exception("create_project failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.patch("/{project_id}", summary="Update a project", response_model=ProjectOut)
def patch_project(project_id: int, body: ProjectUpdate, db: DbDep):
    try:
        return update_project(db, project_id, body.model_dump(exclude_unset=True))
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


@router.get("/{project_id}/members", summary="List project members", response_model=ProjectEmployeeList)
def get_members(project_id: int, db: DbDep):
    return {"members": list_project_members(db, project_id)}


@router.post("/{project_id}/members", summary="Add/Update a project member")
def post_member(project_id: int, body: ProjectEmployeeCreate, db: DbDep):
    try:
        add_project_member(
            db,
            project_id=project_id,
            employee_id=body.employee_id,
            role=body.role,
            start_date=body.start_date,
            end_date=body.end_date,
        )
        return {"ok": True}
    except KeyError:
        raise HTTPException(status_code=422, detail="employee_id is required")
    except Exception as exc:
        logger.exception("add_project_member failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{project_id}/members/{employee_id}", summary="Remove a project member")
def delete_member(project_id: int, employee_id: int, db: DbDep):
    try:
        remove_project_member(db, project_id=project_id, employee_id=employee_id)
        return {"ok": True}
    except Exception as exc:
        logger.exception("remove_project_member failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{project_id}/requirements", summary="List required document types for project", response_model=ProjectRequirementList)
def get_requirements(project_id: int, db: DbDep):
    return {"requirements": list_project_requirements(db, project_id)}


@router.put("/{project_id}/requirements", summary="Set required document types for project")
def put_requirements(project_id: int, body: ProjectRequirementUpdate, db: DbDep):
    ids = body.document_type_ids
    if not isinstance(ids, list):
        raise HTTPException(status_code=422, detail="document_type_ids must be a list[int]")
    try:
        set_project_requirements(db, project_id, [int(x) for x in ids])
        return {"ok": True}
    except Exception as exc:
        logger.exception("set_project_requirements failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{project_id}/members/batch", summary="Batch add project members", status_code=status.HTTP_200_OK)
def post_members_batch(project_id: int, body: ProjectEmployeeBatchCreate, db: DbDep):
    try:
        add_project_members_batch(db, project_id, [member.model_dump() for member in body.employees])
        return {"ok": True}
    except Exception as exc:
        logger.exception("add_project_members_batch failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{project_id}/tree", summary="Get project organizational tree")
def get_project_tree_endpoint(project_id: int, db: DbDep):
    try:
        proj = get_project(db, project_id)
        return {"tree_data": proj.get("tree_data")}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("get_project_tree failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/{project_id}/tree", summary="Update project organizational tree", status_code=status.HTTP_200_OK)
def put_project_tree(project_id: int, body: ProjectTreeUpdate, db: DbDep):
    try:
        get_project(db, project_id)  # verify existence
        update_project_tree(db, project_id, body.tree_data)
        return {"ok": True}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("update_project_tree failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


