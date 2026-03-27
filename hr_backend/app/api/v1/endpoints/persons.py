from fastapi import APIRouter, HTTPException, status
import shutil
from fastapi.responses import FileResponse

from app.api.v1.deps import SettingsDep, DbDep
from app.utils.name_normalizer import normalize_name
from app.schemas.hr import OutputListResponse, PersonFolder
from app.db.postgres import (
    get_employee_by_code,
    delete_employee_and_documents,
    delete_document,
    rename_document,
    rename_employee_documents_folder,
    get_status_id_by_name,
)

router = APIRouter(prefix="/persons", tags=["persons"])


@router.post(
    "",
    summary="Create (or ensure) a person folder in PEOPLE_DIR",
    status_code=status.HTTP_200_OK,
)
def ensure_person_folder(body: dict, settings: SettingsDep) -> dict:
    name_raw = (body.get("name") or "").strip()
    if not name_raw:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="name is required")

    folder_name = normalize_name(name_raw)
    person_dir = settings.people_dir / folder_name
    person_dir.mkdir(parents=True, exist_ok=True)
    return {"name": name_raw, "folder": folder_name, "path": str(person_dir)}

@router.get(
    "",
    summary="List all persons and their files in the people directory",
    response_model=OutputListResponse,
)
def list_persons(settings: SettingsDep, db: DbDep, terminated: bool = False) -> OutputListResponse:
    try:
        terminated_id = get_status_id_by_name(db, 'Terminated')
        persons: list[PersonFolder] = []
        for entry in sorted(settings.people_dir.iterdir()):
            if entry.is_dir():
                display_name = None
                emp = get_employee_by_code(db, entry.name)
                current_status = emp.status_id if emp else None
                is_terminated = current_status == terminated_id
                
                if terminated and not is_terminated:
                    continue
                if not terminated and is_terminated:
                    continue

                if emp:
                    display_name = emp.full_name
                persons.append(
                    PersonFolder(
                        name=entry.name,
                        display_name=display_name,
                        files=sorted(f.name for f in entry.iterdir() if f.is_file()),
                    )
                )
        return OutputListResponse(persons=persons)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


from pydantic import BaseModel
from typing import Optional

class SearchFolderRequest(BaseModel):
    name: Optional[str] = None
    cccd: Optional[str] = None
    mnv: Optional[str] = None

@router.post(
    "/search-folders",
    summary="Search person folders by Name, CCCD, or MNV",
    response_model=OutputListResponse,
)
def search_folders(body: SearchFolderRequest, settings: SettingsDep, db: DbDep) -> OutputListResponse:
    from psycopg2.extras import RealDictCursor
    from pathlib import Path
    
    query = """
        SELECT DISTINCT e.folder_path, e.full_name
        FROM employees e
        LEFT JOIN documents d ON e.id = d.employee_id
        WHERE 1=1
    """
    params = []
    
    if body.name:
        query += " AND e.full_name ILIKE %s"
        params.append(f"%{body.name}%")
    if body.mnv:
        query += " AND e.employee_code = %s"
        params.append(body.mnv)
    if body.cccd:
        query += " AND (e.employee_code = %s OR d.document_number = %s)"
        params.extend([body.cccd, body.cccd])
        
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        
    persons: list[PersonFolder] = []
    for row in rows:
        folder_path = row["folder_path"]
        if folder_path:
            folder_name = Path(folder_path).name
            entry = settings.people_dir / folder_name
            if entry.exists() and entry.is_dir():
                persons.append(
                    PersonFolder(
                        name=entry.name,
                        display_name=row["full_name"],
                        files=sorted(f.name for f in entry.iterdir() if f.is_file() and not f.name.endswith(".meta.json") and f.name != "_display_name.txt"),
                    )
                )
                
    return OutputListResponse(persons=persons)


@router.get(
    "/{person}/download",
    summary="Download all files for a person as a ZIP archive",
)
def download_person(person: str, settings: SettingsDep) -> FileResponse:
    import tempfile
    folder = settings.people_dir / person
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    try:
        folder.resolve().relative_to(settings.people_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    temp_zip.close()
    
    try:
        from pathlib import Path
        shutil.make_archive(temp_zip.name.replace(".zip", ""), 'zip', folder)
        return FileResponse(
            path=f"{temp_zip.name}",
            media_type="application/zip",
            filename=f"{person}.zip"
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get(
    "/{person}/{filename}",
    summary="Serve a single file from the people directory for preview",
)
def serve_person_file(person: str, filename: str, settings: SettingsDep) -> FileResponse:
    from urllib.parse import quote

    file_path = settings.people_dir / person / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    try:
        file_path.resolve().relative_to(settings.people_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Reuse _MIME_MAP or default
    _MIME_MAP = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    media_type = _MIME_MAP.get(file_path.suffix.lower(), "application/octet-stream")

    # ✅ FIX: Encode filename properly for unicode characters
    # Use RFC 5987 encoding for Content-Disposition header
    encoded_filename = quote(filename.encode('utf-8'))

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}"
        },
    )


@router.delete(
    "/batch",
    summary="Batch delete multiple persons folders",
    status_code=status.HTTP_200_OK,
)
def delete_persons_batch(body: dict, settings: SettingsDep, db: DbDep) -> dict:
    persons = body.get("persons", [])
    if not isinstance(persons, list):
        raise HTTPException(status_code=422, detail="'persons' array is required")
        
    results = []
    for person in persons:
        try:
            folder = settings.people_dir / person
            hard_deleted = delete_employee_and_documents(db, person, hard_delete=True)
            if folder.exists() and folder.is_dir():
                shutil.rmtree(folder)
            results.append({"person": person, "success": True})
        except Exception as exc:
            results.append({"person": person, "success": False, "error": str(exc)})
            
    return {"results": results}


@router.delete(
    "/{person}",
    summary="Delete an entire person's folder from people storage",
    status_code=status.HTTP_200_OK,
)
def delete_person_data(person: str, settings: SettingsDep, db: DbDep) -> dict:
    folder = settings.people_dir / person
    if folder.exists():
        try:
            folder.resolve().relative_to(settings.people_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
            
    try:
        # Force hard-delete on DB records to revert the soft-delete lock feature
        hard_deleted = delete_employee_and_documents(db, person, hard_delete=True)
        # Always clean up the physical storage folder when calling Delete
        if folder.exists() and folder.is_dir():
            shutil.rmtree(folder)
        return {"deleted": person, "hard_deleted": hard_deleted}
    except OSError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post(
    "/delete-batch",
    summary="Batch soft-delete multiple employee records from DB and output",
    status_code=status.HTTP_200_OK,
)
def batch_delete_employee_data(body: dict, db: DbDep) -> dict:
    persons = body.get("persons", [])
    if not isinstance(persons, list):
        raise HTTPException(status_code=422, detail="'persons' must be a list of strings")
    results = []
    for person in persons:
        try:
            d = delete_employee_and_documents(db, person)
            results.append({"person": person, "success": d})
        except Exception as exc:
            results.append({"person": person, "success": False, "error": str(exc)})
    return {"results": results}


@router.patch(
    "/{person}",
    summary="Rename an entire person's folder",
    status_code=status.HTTP_200_OK,
)
def rename_person_data_folder(person: str, body: dict, settings: SettingsDep, db: DbDep) -> dict:
    new_name_raw: str = body.get("new_name", "").strip()
    if not new_name_raw:
        raise HTTPException(status_code=422, detail="new_name is required")
        
    from app.utils.name_normalizer import normalize_name
    new_name = normalize_name(new_name_raw)

    if new_name == person:
        return {"renamed_to": new_name}

    src = settings.people_dir / person
    dst = settings.people_dir / new_name

    if not src.exists() or not src.is_dir():
        raise HTTPException(status_code=404, detail="Person folder not found")
    if dst.exists():
        raise HTTPException(status_code=409, detail="A folder with that name already exists")
        
    try:
        src.resolve().relative_to(settings.people_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    emp = get_employee_by_code(db, person)
    if emp:
        if get_employee_by_code(db, new_name):
            raise HTTPException(status_code=409, detail="Employee code already exists in database")

    try:
        src.rename(dst)
        if emp:
            from app.db.employee_repo import update_employee
            update_employee(db, emp.id, {
                "employee_code": new_name,
                "folder_path": str(dst),
                "full_name": new_name_raw
            })
            rename_employee_documents_folder(db, emp.id, person, new_name)
            
        return {"renamed_to": new_name}
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete(
    "/{person}/{filename}",
    summary="Delete a single file from a person's people folder",
    status_code=status.HTTP_200_OK,
)
def delete_person_file(person: str, filename: str, settings: SettingsDep, db: DbDep) -> dict:
    file_path = settings.people_dir / person / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    try:
        file_path.resolve().relative_to(settings.people_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    try:
        file_path.unlink()
        
        emp = get_employee_by_code(db, person)
        if emp:
            delete_document(db, emp.id, filename)
            
        folder = settings.people_dir / person
        if folder.exists() and not any(folder.iterdir()):
            folder.rmdir()
            delete_employee_and_documents(db, person)
            
        return {"deleted": filename}
    except OSError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.patch(
    "/{person}/{filename}",
    summary="Rename a file inside a person's people folder",
    status_code=status.HTTP_200_OK,
)
def rename_person_file(person: str, filename: str, body: dict, settings: SettingsDep, db: DbDep) -> dict:
    new_name: str = body.get("new_name", "").strip()
    if not new_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="new_name is required")

    src = settings.people_dir / person / filename
    dst = settings.people_dir / person / new_name

    if not src.exists() or not src.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    if dst.exists():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A file with that name already exists")
    try:
        src.resolve().relative_to(settings.people_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    try:
        src.rename(dst)
        
        emp = get_employee_by_code(db, person)
        if emp:
            rename_document(db, emp.id, filename, new_name, str(dst.relative_to(settings.people_dir)))
            
        return {"renamed_to": new_name}
    except OSError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post(
    "/download-batch",
    summary="Download multiple persons' folders as a single ZIP archive",
)
def download_persons_batch(body: dict, settings: SettingsDep) -> FileResponse:
    import tempfile
    import shutil
    from pathlib import Path

    persons: list[str] = body.get("persons", [])
    if not persons:
        persons = [entry.name for entry in settings.people_dir.iterdir() if entry.is_dir()]
        
    if not persons:
        raise HTTPException(status_code=404, detail="No persons found to download")

    temp_dir = Path(tempfile.mkdtemp())
    try:
        for person in persons:
            src = settings.people_dir / person
            if src.exists() and src.is_dir():
                try:
                    src.resolve().relative_to(settings.people_dir.resolve())
                    dst = temp_dir / person
                    shutil.copytree(src, dst)
                except Exception:
                    continue

        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        temp_zip.close()
        shutil.make_archive(temp_zip.name.replace(".zip", ""), 'zip', temp_dir)
        
        return FileResponse(
            path=f"{temp_zip.name}",
            media_type="application/zip",
            filename="Ho_so_nhan_su_batch.zip"
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post(
    "/delete-batch",
    summary="Delete multiple persons' folders in bulk",
    status_code=status.HTTP_200_OK,
)
def delete_persons_batch(body: dict, settings: SettingsDep, db: DbDep) -> dict:
    persons: list[str] = body.get("persons", [])
    if not persons:
        persons = [entry.name for entry in settings.people_dir.iterdir() if entry.is_dir()]

    deleted_count = 0
    for person in persons:
        folder = settings.people_dir / person
        if folder.exists() and folder.is_dir():
            try:
                folder.resolve().relative_to(settings.people_dir.resolve())
                hard_deleted = delete_employee_and_documents(db, person)
                if hard_deleted:
                    shutil.rmtree(folder)
                deleted_count += 1
            except Exception:
                continue

    return {"deleted_count": deleted_count}
