import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.v1.deps import DbDep, HRServiceDep, SettingsDep
from app.models.document import SUPPORTED_MIME_TYPES
from app.schemas.hr import OutputListResponse, PersonFolder, ProcessDocumentsResponse

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)

_MIME_MAP = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


@router.post(
    "/upload",
    summary="Upload one or more HR documents to the input directory",
    status_code=status.HTTP_200_OK,
)
async def upload_documents(
    files: list[UploadFile],
    settings: SettingsDep,
) -> dict:
    """Accept multiple files and save them to INPUT_DIR for later processing."""
    saved: list[str] = []
    rejected: list[str] = []

    try:
        for upload in files:
            suffix = Path(upload.filename).suffix.lower()
            if suffix not in SUPPORTED_MIME_TYPES:
                rejected.append(upload.filename)
                continue

            dest = settings.input_dir / upload.filename
            content = await upload.read()
            dest.write_bytes(content)
            saved.append(upload.filename)
            logger.info("Saved upload: %s", upload.filename)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {exc}",
        ) from exc

    return {"saved": saved, "rejected": rejected}


@router.post(
    "/process",
    summary="Classify all documents in the input directory using Gemini AI",
    response_model=ProcessDocumentsResponse,
)
async def process_documents(hr: HRServiceDep) -> ProcessDocumentsResponse:
    try:
        return await hr.process_documents()
    except Exception as exc:
        logger.exception("process_documents failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/output/{person}/commit",
    summary="Commit a person's staged output to PEOPLE_DIR (create folder if missing)",
    status_code=status.HTTP_200_OK,
)
def commit_person(person: str, hr: HRServiceDep, db: DbDep) -> dict:
    try:
        result = hr.commit_person(person=person, db=db)
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("commit_person failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post(
    "/output/{person}/commit_files",
    summary="Commit specific files from a person's staged output to a target person's PEOPLE_DIR",
    status_code=status.HTTP_200_OK,
)
def commit_files(person: str, body: dict, hr: HRServiceDep, db: DbDep) -> dict:
    files = body.get("files")
    target_person = body.get("target_person")
    if not isinstance(files, list) or not files:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A list of 'files' is required")
        
    try:
        result = hr.commit_files(source_person=person, filenames=files, target_person=target_person, db=db)
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("commit_files failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post(
    "/commit",
    summary="Commit all staged output persons into PEOPLE_DIR",
    status_code=status.HTTP_200_OK,
)
def commit_all(hr: HRServiceDep, db: DbDep) -> dict:
    try:
        return hr.commit_all(db=db)
    except Exception as exc:
        logger.exception("commit_all failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

@router.delete(
    "/input",
    summary="Clear all files from the input directory",
    status_code=status.HTTP_200_OK,
)
def clear_input(settings: SettingsDep) -> dict:
    try:
        removed: list[str] = []
        for f in settings.input_dir.iterdir():
            if f.is_file():
                f.unlink()
                removed.append(f.name)
        return {"removed": removed}
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "/output",
    summary="List all organised persons and their files in the output directory",
    response_model=OutputListResponse,
)
def list_output(settings: SettingsDep) -> OutputListResponse:
    try:
        persons: list[PersonFolder] = []
        for entry in sorted(settings.output_dir.iterdir()):
            if entry.is_dir():
                display_name = None
                meta = entry / "_display_name.txt"
                try:
                    if meta.exists():
                        display_name = meta.read_text(encoding="utf-8").strip() or None
                except Exception:
                    display_name = None
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


@router.get(
    "/output/{person}/{filename}",
    summary="Serve a single file from the output directory for preview",
)
def serve_output_file(person: str, filename: str, settings: SettingsDep) -> FileResponse:
    """Stream a file from output/<person>/<filename> so the FE can preview it."""
    file_path = settings.output_dir / person / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    # Prevent path traversal
    try:
        file_path.resolve().relative_to(settings.output_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    media_type = _MIME_MAP.get(file_path.suffix.lower(), "application/octet-stream")
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f"inline; filename=\"{filename}\""},
    )


@router.delete(
    "/output",
    summary="Clear the entire output directory",
    status_code=status.HTTP_200_OK,
)
def clear_output(settings: SettingsDep) -> dict:
    try:
        shutil.rmtree(settings.output_dir, ignore_errors=True)
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        return {"detail": "Output directory cleared."}
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.delete(
    "/output/{person}/{filename}",
    summary="Delete a single file from a person's folder",
    status_code=status.HTTP_200_OK,
)
def delete_output_file(person: str, filename: str, settings: SettingsDep) -> dict:
    file_path = settings.output_dir / person / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    try:
        file_path.resolve().relative_to(settings.output_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    try:
        file_path.unlink()
        # Remove person folder if now empty
        folder = settings.output_dir / person
        if folder.exists() and not any(folder.iterdir()):
            folder.rmdir()
        return {"deleted": filename}
    except OSError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.patch(
    "/output/{person}/{filename}",
    summary="Rename a file inside a person's folder",
    status_code=status.HTTP_200_OK,
)
def rename_output_file(person: str, filename: str, body: dict, settings: SettingsDep) -> dict:
    new_name: str = body.get("new_name", "").strip()
    if not new_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="new_name is required")

    src = settings.output_dir / person / filename
    dst = settings.output_dir / person / new_name

    if not src.exists() or not src.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    if dst.exists():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A file with that name already exists")
    try:
        src.resolve().relative_to(settings.output_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    try:
        src.rename(dst)
        return {"renamed_to": new_name}
    except OSError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
@router.delete(
    "/output/{person}",
    summary="Delete an entire person's folder",
    status_code=status.HTTP_200_OK,
)
def delete_person(person: str, settings: SettingsDep) -> dict:
    folder = settings.output_dir / person
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    try:
        folder.resolve().relative_to(settings.output_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    try:
        shutil.rmtree(folder)
        return {"deleted": person}
    except OSError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get(
    "/output/{person}/download",
    summary="Download all files for a person as a ZIP archive",
)
def download_person(person: str, settings: SettingsDep) -> FileResponse:
    import tempfile
    folder = settings.output_dir / person
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    try:
        folder.resolve().relative_to(settings.output_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Create a temporary ZIP file
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    temp_zip.close()
    
    try:
        shutil.make_archive(temp_zip.name.replace(".zip", ""), 'zip', folder)
        return FileResponse(
            path=f"{temp_zip.name}",
            media_type="application/zip",
            filename=f"{person}.zip"
        )
    except Exception as exc:
        if Path(temp_zip.name).exists():
            Path(temp_zip.name).unlink()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
