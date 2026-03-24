from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Gemini
    gemini_api_key: Optional[str] = None
    gemini_api_keys: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash"
    gemini_concurrency: int = 1

    @property
    def get_api_keys(self) -> list[str]:
        if self.gemini_api_keys:
            keys = [k.strip() for k in self.gemini_api_keys.split(",") if k.strip()]
            if keys:
                return keys
        return [self.gemini_api_key]

    # Storage (staging)
    # You can set STORAGE_ROOT to move all storage outside the backend folder.
    storage_root: Optional[Path] = None
    input_dir: Path = Path("storage/input")
    output_dir: Path = Path("storage/output")
    people_dir: Path = Path("storage/people")

    # DB
    database_url: str = "postgresql://localhost/employee_management"

    # Face recognition
    face_model: str = "Facenet512"
    face_detector: str = "retinaface"
    face_threshold: float = 0.4

    # API
    app_title: str = "HR Document AI"
    app_version: str = "1.0.0"
    debug: bool = False

    def model_post_init(self, __context) -> None:
        # Derive paths from STORAGE_ROOT if the caller didn't override them.
        if self.storage_root is not None:
            root = Path(self.storage_root)
            if self.input_dir in (Path("storage/input"), Path("."), Path("")):
                self.input_dir = root / "input"
            if self.output_dir in (Path("storage/output"), Path("."), Path("")):
                self.output_dir = root / "output"
            if self.people_dir in (Path("storage/people"), Path("."), Path("")):
                self.people_dir = root / "people"

        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.people_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
