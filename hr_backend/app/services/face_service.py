import logging
from pathlib import Path
from typing import Optional
import concurrent.futures

import numpy as np
import pymupdf
from deepface import DeepFace

from hr_backend.app.core.config import Settings
from hr_backend.app.core.exceptions import FaceEmbeddingError, NoAnchorsError

logger = logging.getLogger(__name__)


class FaceService:
    def __init__(self, settings: Settings) -> None:
        self._model = settings.face_model
        self._detector = settings.face_detector
        self._threshold = settings.face_threshold
        self._concurrency = max(1, settings.gemini_concurrency)
        logger.info(
            "FaceService initialised model=%s detector=%s threshold=%.2f concurrency=%d",
            self._model,
            self._detector,
            self._threshold,
            self._concurrency,
        )

    # ── Low-level helpers ────────────────────────────────────────────────────

    def pdf_first_page_to_image(self, pdf_path: Path, out_path: Path) -> None:
        """Render the first page of *pdf_path* to *out_path* at 4× scale."""
        doc = pymupdf.open(str(pdf_path))
        page = doc[0]
        pix = page.get_pixmap(matrix=pymupdf.Matrix(4, 4))
        pix.save(str(out_path))
        logger.debug("Rendered %s -> %s", pdf_path.name, out_path.name)

    def get_embedding(self, img_path: Path, enforce: bool = True) -> np.ndarray:
        """Extract a face embedding vector from *img_path*.

        Args:
            img_path: Path to an image file.
            enforce: Whether to raise when no face is detected.

        Returns:
            1-D numpy array of shape (embedding_dim,).

        Raises:
            FaceEmbeddingError: DeepFace could not extract an embedding.
        """
        result = DeepFace.represent(
            img_path=str(img_path),
            model_name=self._model,
            detector_backend=self._detector,
            enforce_detection=enforce,
        )
        if not result:
            raise FaceEmbeddingError(img_path.name, "DeepFace returned empty result")
        return np.array(result[0]["embedding"])

    @staticmethod
    def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
        """Return cosine distance in [0, 2] between two vectors."""
        return float(1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    # ── High-level operations ────────────────────────────────────────────────

    def build_anchors(self, persons_dir: Path, tmp_dir: Path) -> dict[str, np.ndarray]:
        """Build face embeddings for every person that has a CCCD.pdf.

        Returns:
            Mapping of person folder name -> embedding vector.
        """
        anchors: dict[str, np.ndarray] = {}
        tmp_dir.mkdir(parents=True, exist_ok=True)

        def _process_anchor(idx: int, person_folder: Path) -> tuple[str, Optional[np.ndarray]]:
            cccd_file = person_folder / "CCCD.pdf"
            if not cccd_file.exists():
                logger.warning("No CCCD.pdf in %s – skipped", person_folder.name)
                return person_folder.name, None

            logger.info("Building anchor for %s…", person_folder.name)
            tmp_img = tmp_dir / f"anchor_{idx}.jpg"
            try:
                self.pdf_first_page_to_image(cccd_file, tmp_img)
            except Exception as e:
                logger.error("Failed to render PDF for anchor %s: %s", person_folder.name, e)
                return person_folder.name, None

            embedding = self._get_embedding_with_fallback(tmp_img, person_folder.name)
            if embedding is not None:
                logger.info("Anchor OK: %s", person_folder.name)
            else:
                logger.warning("Anchor FAILED: %s", person_folder.name)
                
            return person_folder.name, embedding

        folders_to_process = [
            (i, p) for i, p in enumerate(sorted(persons_dir.iterdir()))
            if p.is_dir() and p.name != "_unknown"
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=self._concurrency) as executor:
            futures = {
                executor.submit(_process_anchor, idx, folder): folder.name
                for idx, folder in folders_to_process
            }
            
            for future in concurrent.futures.as_completed(futures):
                person_name = futures[future]
                try:
                    _, embedding = future.result()
                    if embedding is not None:
                        anchors[person_name] = embedding
                except Exception as e:
                    logger.error("Error building anchor for %s: %s", person_name, e)

        return anchors

    def match_photo(
        self,
        photo_path: Path,
        anchors: dict[str, np.ndarray],
    ) -> tuple[Optional[str], Optional[float]]:
        """Match *photo_path* against anchor embeddings.

        Returns:
            (person_name, distance) if match found, or (None, best_distance) otherwise.

        Raises:
            NoAnchorsError: anchors dict is empty.
            FaceEmbeddingError: face extraction failed for the photo.
        """
        if not anchors:
            raise NoAnchorsError()

        embedding = self._get_embedding_with_fallback(photo_path, photo_path.name)
        if embedding is None:
            raise FaceEmbeddingError(photo_path.name, "could not extract face with or without enforcement")

        anchor_names = list(anchors.keys())
        distances = [self.cosine_distance(embedding, v) for v in anchors.values()]
        best_idx = int(np.argmin(distances))
        best_dist = distances[best_idx]

        if best_dist < self._threshold:
            return anchor_names[best_idx], best_dist

        return None, best_dist

    # ── Private ──────────────────────────────────────────────────────────────

    def _get_embedding_with_fallback(
        self,
        img_path: Path,
        label: str,
    ) -> Optional[np.ndarray]:
        """Try enforce=True, fall back to enforce=False, return None on failure."""
        try:
            return self.get_embedding(img_path, enforce=True)
        except Exception as first_exc:
            logger.debug("enforce=True failed for %s: %s – retrying…", label, first_exc)

        try:
            return self.get_embedding(img_path, enforce=False)
        except Exception as second_exc:
            logger.warning("enforce=False also failed for %s: %s", label, second_exc)
            return None
