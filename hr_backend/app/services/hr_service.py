import asyncio
import logging
import shutil
import concurrent.futures
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.models.document import SUPPORTED_MIME_TYPES, UNKNOWN_FOLDER
from app.schemas.hr import (
    FaceMatchResult,
    FileProcessResult,
    MatchFacesResponse,
    ProcessDocumentsResponse,
)
from app.services.face_service import FaceService
from app.services.gemini_service import GeminiService
from app.utils.file_utils import copy_to_output, move_to_output, safe_destination
from app.utils.name_normalizer import normalize_name
from app.db.postgres import insert_document, upsert_employee

logger = logging.getLogger(__name__)

_TMP_DIR = Path("_tmp_cccd")
_DISPLAY_NAME_FILE = "_display_name.txt"


class HRService:
    """Orchestrates document classification and face-matching workflows."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._gemini = GeminiService(settings)
        self._face = FaceService(settings)

    # ── Public API ───────────────────────────────────────────────────────────

    async def process_documents(self) -> ProcessDocumentsResponse:
        """Classify every supported file in INPUT_DIR and copy to OUTPUT_DIR.

        Each file is uploaded to Gemini to detect the owner name and document
        type, then saved to output/<person_folder>/<doc_type><ext>.
        """
        input_dir: Path = self._settings.input_dir
        output_dir: Path = self._settings.output_dir

        files = [
            f for f in input_dir.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_MIME_TYPES
        ]

        if not files:
            logger.warning("No supported files found in %s", input_dir)
            return ProcessDocumentsResponse(total=0, succeeded=0, failed=0, results=[])

        logger.info("Found %d file(s) to process", len(files))

        # sem = asyncio.Semaphore(max(1, int(self._settings.gemini_concurrency)))
        sem = asyncio.Semaphore(1)

        async def run_one(file_path: Path) -> FileProcessResult:
            async with sem:
                return await asyncio.to_thread(self._process_single_document, file_path, output_dir)

        results = await asyncio.gather(*(run_one(p) for p in files))

        succeeded = sum(1 for r in results if r.status == "ok")
        return ProcessDocumentsResponse(
            total=len(results),
            succeeded=succeeded,
            failed=len(results) - succeeded,
            results=results,
        )

    def commit_person(self, *, person: str, db: Any) -> dict:
        """Move staged output/<person> files into PEOPLE_DIR/<person>.

        Final filenames follow: <DOC_TYPE>_<PersonFolder><ext> (with _N suffix on collision).
        Also upserts an employee row + inserts documents rows.
        """
        person_folder = normalize_name(person)
        src_dir = self._settings.output_dir / person
        if not src_dir.exists() or not src_dir.is_dir():
            raise FileNotFoundError(f"Person folder not found in output: {person}")

        dest_person_dir = self._settings.people_dir / person_folder
        dest_person_dir.mkdir(parents=True, exist_ok=True)

        display_name = person
        meta_path = src_dir / _DISPLAY_NAME_FILE
        try:
            if meta_path.exists():
                display_name = meta_path.read_text(encoding="utf-8").strip() or display_name
                meta_path.unlink()
        except Exception:
            pass

        emp = upsert_employee(
            db,
            employee_code=person_folder,
            full_name=display_name,
            folder_path=str(dest_person_dir),
        )

        moved: list[dict] = []
        for f in sorted(p for p in src_dir.iterdir() if p.is_file() and p.name != _DISPLAY_NAME_FILE):
            suffix = f.suffix.lower()
            base = f.stem
            # base might be "CCCD" or "CCCD_2" etc. Strip trailing _N.
            doc_type = base.rsplit("_", 1)[0] if base.rsplit("_", 1)[-1].isdigit() else base

            # Về sau cần format lại tên file có gì the fomart ở đây
            final_base = f"{doc_type}_{person_folder}"

            dest = safe_destination(dest_person_dir, final_base, suffix)
            move_to_output(f, dest)
            moved.append(
                {
                    "from": str(f.relative_to(self._settings.output_dir)),
                    "to": str(dest.relative_to(self._settings.people_dir)),
                }
            )
            insert_document(
                db,
                employee_id=emp.id,
                doc_type=doc_type,
                filename=dest.name,
                rel_path=str(dest.relative_to(self._settings.people_dir)),
            )

        # Remove empty staged folder if all files were moved.
        try:
            if src_dir.exists() and not any(src_dir.iterdir()):
                src_dir.rmdir()
        except Exception:
            pass

        return {
            "person": person_folder,
            "display_name": display_name,
            "person_folder": person_folder,
            "people_path": str(dest_person_dir),
            "moved": moved,
        }

    def commit_files(self, *, source_person: str, filenames: list[str], target_person: str = None, db: Any = None) -> dict:
        """Move specific files from a staged folder into a target person's folder.
        If target_person is None, defaults to source_person.
        """
        source_folder = normalize_name(source_person)
        src_dir = self._settings.output_dir / source_person
        if not src_dir.exists() or not src_dir.is_dir():
            raise FileNotFoundError(f"Person folder not found in output: {source_person}")

        final_person = target_person if target_person else source_person
        final_person_folder = normalize_name(final_person)
        dest_person_dir = self._settings.people_dir / final_person_folder
        dest_person_dir.mkdir(parents=True, exist_ok=True)

        display_name = final_person
        if final_person == source_person:
            meta_path = src_dir / _DISPLAY_NAME_FILE
            try:
                if meta_path.exists():
                    display_name = meta_path.read_text(encoding="utf-8").strip() or display_name
                    meta_path.unlink()
            except Exception:
                pass

        emp = upsert_employee(
            db,
            employee_code=final_person_folder,
            full_name=display_name,
            folder_path=str(dest_person_dir),
        )

        moved: list[dict] = []
        for filename in filenames:
            if filename == _DISPLAY_NAME_FILE:
                continue
                
            f = src_dir / filename
            if not f.exists() or not f.is_file():
                continue

            suffix = f.suffix.lower()
            base = f.stem
            doc_type = base.rsplit("_", 1)[0] if base.rsplit("_", 1)[-1].isdigit() else base

            final_base = f"{doc_type}_{final_person_folder}"
            dest = safe_destination(dest_person_dir, final_base, suffix)
            move_to_output(f, dest)
            moved.append(
                {
                    "from": str(f.relative_to(self._settings.output_dir)),
                    "to": str(dest.relative_to(self._settings.people_dir)),
                }
            )
            insert_document(
                db,
                employee_id=emp.id,
                doc_type=doc_type,
                filename=dest.name,
                rel_path=str(dest.relative_to(self._settings.people_dir)),
            )

        # Remove empty staged folder if all files were moved.
        try:
            if src_dir.exists() and not any(src_dir.iterdir()):
                src_dir.rmdir()
        except Exception:
            pass

        return {
            "source_person": source_person,
            "target_person": final_person,
            "target_folder": final_person_folder,
            "moved": moved,
        }

    def commit_all(self, db: Any) -> dict:
        output_dir = self._settings.output_dir
        committed: list[dict] = []
        skipped: list[str] = []

        for entry in sorted(output_dir.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name == UNKNOWN_FOLDER:
                skipped.append(entry.name)
                continue
            try:
                committed.append(self.commit_person(person=entry.name, db=db))
            except Exception:
                skipped.append(entry.name)

        return {"committed": committed, "skipped": skipped}

    def match_faces(self) -> MatchFacesResponse:
        """Match unknown photo files to known persons via face recognition.

        1. Build anchor embeddings from each person's CCCD.pdf.
        2. For every image in output/_unknown, find the closest anchor.
        3. Move matched photos to the correct person folder.
        """
        output_dir: Path = self._settings.output_dir
        photos_dir = output_dir / UNKNOWN_FOLDER

        _TMP_DIR.mkdir(parents=True, exist_ok=True)

        anchors = self._face.build_anchors(output_dir, _TMP_DIR)
        logger.info("Built %d anchor(s): %s", len(anchors), list(anchors.keys()))

        results: list[FaceMatchResult] = []

        if photos_dir.exists():
            photo_files = sorted(
                f for f in photos_dir.iterdir()
                if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png"}
            )
            
            max_workers = max(1, int(self._settings.gemini_concurrency))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._match_single_photo, photo, anchors, output_dir): photo 
                    for photo in photo_files
                }
                for future in concurrent.futures.as_completed(futures):
                    try:
                        results.append(future.result())
                    except Exception as e:
                        logger.error("Failed to match %s: %s", futures[future].name, e)

        shutil.rmtree(_TMP_DIR, ignore_errors=True)

        return MatchFacesResponse(
            anchors_built=len(anchors),
            photos_processed=len(results),
            results=results,
        )

    # ── Private helpers ──────────────────────────────────────────────────────

    def _process_single_document(
        self,
        file_path: Path,
        output_dir: Path,
    ) -> FileProcessResult:
        try:
            # Create a Gemini client per worker thread for safer concurrency.
            info = GeminiService(self._settings).analyze_document(file_path)
            folder_name = normalize_name(info.person_name) if info.person_name else UNKNOWN_FOLDER
            dest_dir = output_dir / folder_name
            dest_dir.mkdir(parents=True, exist_ok=True)
            if info.person_name and folder_name != UNKNOWN_FOLDER:
                try:
                    (dest_dir / _DISPLAY_NAME_FILE).write_text(info.person_name, encoding="utf-8")
                except Exception:
                    pass

            # dest = safe_destination(dest_dir, info.doc_type, file_path.suffix.lower())
            # SAU (đúng)
            doc_type_str = info.doc_type.value if hasattr(info.doc_type, "value") else str(info.doc_type)
            # Remove class prefix if present (e.g. DocType.CCCD -> CCCD)
            if doc_type_str.startswith("DocType."):
                doc_type_str = doc_type_str.replace("DocType.", "")
                
            dest = safe_destination(dest_dir, doc_type_str, file_path.suffix.lower())
            move_to_output(file_path, dest)

            logger.info("%s -> %s", file_path.name, dest.relative_to(output_dir))
            return FileProcessResult(
                original_filename=file_path.name,
                person_name=info.person_name,
                doc_type=info.doc_type,
                destination=str(dest.relative_to(output_dir)),
            )
        except Exception as exc:
            logger.error("Failed to process %s: %s", file_path.name, exc)
            return FileProcessResult(
                original_filename=file_path.name,
                person_name=None,
                doc_type="Khac",
                destination="",
                status="error",
                error=str(exc),
            )

    def _match_single_photo(
        self,
        photo: Path,
        anchors: dict,
        output_dir: Path,
    ) -> FaceMatchResult:
        try:
            matched_person, distance = self._face.match_photo(photo, anchors)
            dest_folder = matched_person if matched_person else UNKNOWN_FOLDER
            dest_dir = output_dir / dest_folder
            dest = safe_destination(dest_dir, "Anh_the", photo.suffix.lower())
            move_to_output(photo, dest)

            logger.info(
                "%s -> %s (dist=%.3f)",
                photo.name,
                dest.relative_to(output_dir),
                distance if distance is not None else -1,
            )
            return FaceMatchResult(
                photo_filename=photo.name,
                matched_person=matched_person,
                distance=distance,
                destination=str(dest.relative_to(output_dir)),
            )
        except Exception as exc:
            logger.error("Failed to match %s: %s", photo.name, exc)
            return FaceMatchResult(
                photo_filename=photo.name,
                matched_person=None,
                distance=None,
                destination="",
                status="error",
                error=str(exc),
            )
