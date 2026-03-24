import json
import logging
import re
import threading
import itertools
from pathlib import Path

import google.generativeai as genai
from google.generativeai import client as genai_client

from hr_backend.app.core.config import Settings
from hr_backend.app.core.exceptions import GeminiAnalysisError, UnsupportedFileTypeError
from hr_backend.app.models.document import SUPPORTED_MIME_TYPES
from hr_backend.app.schemas.hr import DocumentInfo

logger = logging.getLogger(__name__)

# Monkey-patch google.generativeai client manager to be thread-local
# This ensures that each thread getting its own client config via genai.configure() 
# does not overwrite configs of other threads.
if not hasattr(genai_client._client_manager.__class__, "__thread_local__"):
    class ThreadLocalClientManager(threading.local, type(genai_client._client_manager)):
        __thread_local__ = True
        
        def __init__(self):
            super().__init__()
            self.client_config = {}
            self.default_metadata = ()
            self.clients = {}

    genai_client._client_manager = ThreadLocalClientManager()

_PROMPT = """Phân tích tài liệu này và trả về JSON (KHÔNG markdown, chỉ JSON thuần):
{
  "person_name": "Họ tên đầy đủ của chủ nhân tài liệu (hoặc null nếu không xác định được)",
  "doc_type": "Phân loại. Ưu tiên dùng: Anh_the, Cccd, Bang_tot_nghiep, Giay_kham_sk, The_an_toan_ld, Qd_an_toan_ld, Hop_dong_thu_viec, Hop_dong_lao_dong, Cv_kinh_nghiem. Nếu tài liệu không thuộc các loại này, hãy tự đặt tên loại tài liệu mới (ngắn gọn, viết không dấu và dùng gạch dưới, ví dụ: Don_xin_nghi)."
}"""

_api_keys_pool = None
_api_keys_lock = threading.Lock()


class GeminiService:
    def __init__(self, settings: Settings) -> None:
        global _api_keys_pool
        
        with _api_keys_lock:
            if _api_keys_pool is None:
                keys = settings.get_api_keys
                logger.info("Initializing Gemini API keys pool with %d keys", len(keys))
                _api_keys_pool = itertools.cycle(keys)
            
            api_key = next(_api_keys_pool)
            
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(settings.gemini_model)
        
        # Log partial key for tracing without exposing the full key
        safe_key = f"...{api_key[-4:]}" if len(api_key) >= 4 else "***"
        logger.info("GeminiService initialized with model=%s using api_key=%s", settings.gemini_model, safe_key)

    def analyze_document(self, file_path: Path) -> DocumentInfo:
        """Upload *file_path* to Gemini, classify it, and return structured info.

        Raises:
            UnsupportedFileTypeError: file extension is not in SUPPORTED_MIME_TYPES.
            GeminiAnalysisError: Gemini call failed or returned unparseable JSON.
        """
        import time

        suffix = file_path.suffix.lower()
        if suffix not in SUPPORTED_MIME_TYPES:
            raise UnsupportedFileTypeError(suffix)

        mime = SUPPORTED_MIME_TYPES[suffix]
        logger.debug("Uploading %s (%s) to Gemini…", file_path.name, mime)

        uploaded = genai.upload_file(str(file_path), mime_type=mime)
        
        try:
            retries = 5
            response = None
            for attempt in range(retries):
                try:
                    response = self._model.generate_content([_PROMPT, uploaded])
                    break
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "Quota exceeded" in error_str:
                        if attempt < retries - 1:
                            m = re.search(r"Please retry in ([\d\.]+)s", error_str)
                            delay = float(m.group(1)) + 1.0 if m else 15.0
                            logger.warning(
                                "Rate limit hit for %s. Retrying in %.2fs (attempt %d/%d)...",
                                file_path.name, delay, attempt + 1, retries
                            )
                            time.sleep(delay)
                            continue
                    raise
            
            if not response:
                raise GeminiAnalysisError(file_path.name, "Failed to get response after retries")

            raw = response.text.strip()
            raw = re.sub(r'^```[a-z]*\n?', '', raw)
            raw = re.sub(r'\n?```$', '', raw)

            parsed = json.loads(raw)  # raises json.JSONDecodeError on bad response
            if not isinstance(parsed, dict):
                raise GeminiAnalysisError(file_path.name, "response is not a JSON object")

            info = DocumentInfo.model_validate(parsed)
            logger.info(
                "Analyzed %s -> person=%s doc_type=%s",
                file_path.name,
                info.person_name,
                info.doc_type,
            )
            return info
        finally:
            genai.delete_file(uploaded.name)
if __name__ == "__main__":
    from pathlib import Path

    TEST_DIR = Path(r"/Users/anhphuc/Desktop/git_AI_HR/AI_HR_BE/hr_backend/storage/input")  # Thay đường dẫn này
    API_KEY = "AIzaSyDLyrhSK4hYnH1tA8k2b9PMKx7LYZnvPY4"  # Thay key này


    class MockSettings:
        gemini_model = "gemini-2.0-flash"
        get_api_keys = [API_KEY]


    service = GeminiService(MockSettings())

    for file_path in TEST_DIR.glob("*"):
        if file_path.is_file():
            try:
                print(f"\n{'=' * 60}")
                print(f"FILE: {file_path.name}")
                print('=' * 60)

                # Gọi Gemini và lấy raw response
                suffix = file_path.suffix.lower()
                mime = SUPPORTED_MIME_TYPES.get(suffix)
                if not mime:
                    continue

                uploaded = genai.upload_file(str(file_path), mime_type=mime)
                response = service._model.generate_content([_PROMPT, uploaded])

                print("RAW RESPONSE:")
                print(response.text)
                print()

                genai.delete_file(uploaded.name)

            except Exception as e:
                print(f"ERROR: {e}")