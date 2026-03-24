import shutil
from pathlib import Path


def safe_destination(dest_dir: Path, doc_type: str, suffix: str) -> Path:
    """Return a non-colliding path: <dest_dir>/<doc_type>[_N]<suffix>.

    If CCCD.pdf already exists it becomes CCCD_2.pdf, CCCD_3.pdf, …
    """
    candidate = dest_dir / f"{doc_type}{suffix}"
    if not candidate.exists():
        return candidate

    counter = 2
    while True:
        candidate = dest_dir / f"{doc_type}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def copy_to_output(src: Path, dest: Path) -> None:
    """Copy *src* to *dest*, creating parent directories as needed."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def move_to_output(src: Path, dest: Path) -> None:
    """Move *src* to *dest*, creating parent directories as needed."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), dest)
