class HRBaseError(Exception):
    """Base exception for HR backend."""


class UnsupportedFileTypeError(HRBaseError):
    def __init__(self, suffix: str) -> None:
        super().__init__(f"Unsupported file type: '{suffix}'")
        self.suffix = suffix


class GeminiAnalysisError(HRBaseError):
    def __init__(self, filename: str, reason: str) -> None:
        super().__init__(f"Gemini failed to analyze '{filename}': {reason}")
        self.filename = filename
        self.reason = reason


class FaceEmbeddingError(HRBaseError):
    def __init__(self, filename: str, reason: str) -> None:
        super().__init__(f"Could not extract face embedding from '{filename}': {reason}")
        self.filename = filename
        self.reason = reason


class NoAnchorsError(HRBaseError):
    def __init__(self) -> None:
        super().__init__("No anchor embeddings found. Ensure CCCD files exist for known persons.")


class StorageError(HRBaseError):
    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"Storage error at '{path}': {reason}")
        self.path = path
        self.reason = reason
