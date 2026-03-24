# HR Document AI – Backend

Production-grade FastAPI backend for AI-powered HR document management.

## Features

| Feature | Description |
|---|---|
| 📄 Document classification | Upload HR docs → Gemini AI reads and classifies each file |
| 📂 Auto-organisation | Files are copied to `output/<person>/<doc_type>.<ext>` automatically |
| 🤝 Face matching | Unknown photos in `_unknown/` are matched to persons via their CCCD face |
| 🔌 REST API | Full CRUD via `/api/v1` with OpenAPI docs at `/docs` |

---

## Project Structure

```
hr_backend/
├── app/
│   ├── api/v1/
│   │   ├── deps.py               # FastAPI dependency injection
│   │   ├── router.py             # Aggregate all routers
│   │   └── endpoints/
│   │       ├── documents.py      # Upload, process, list, clear
│   │       ├── faces.py          # Face matching
│   │       └── health.py         # Health check
│   ├── core/
│   │   ├── config.py             # Pydantic settings (reads .env)
│   │   ├── exceptions.py         # Domain-specific exceptions
│   │   └── logging.py            # Logging configuration
│   ├── models/
│   │   └── document.py           # DocType enum, MIME_TYPES constant
│   ├── schemas/
│   │   └── hr.py                 # Pydantic request/response models
│   ├── services/
│   │   ├── gemini_service.py     # Gemini AI document analysis
│   │   ├── face_service.py       # DeepFace embedding + matching
│   │   └── hr_service.py         # Orchestration logic
│   ├── utils/
│   │   ├── name_normalizer.py    # Vietnamese → ASCII folder names
│   │   └── file_utils.py         # Safe copy / move helpers
│   └── main.py                   # FastAPI app factory
├── storage/
│   ├── input/                    # Drop files here (or upload via API)
│   └── output/                   # Organised results land here
├── tests/
│   ├── test_name_normalizer.py
│   └── test_file_utils.py
├── .env.example
├── requirements.txt
└── run.py
```

---

## Quickstart

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env .env
# Edit .env and set GEMINI_API_KEY
```

### 3. Run

```bash
python run.py
# or
uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

---

## API Reference

### Health

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/health` | Liveness check |

### Documents

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/documents/upload` | Upload one or more files to INPUT_DIR |
| POST | `/api/v1/documents/process` | Classify all files in INPUT_DIR via Gemini |
| GET | `/api/v1/documents/output` | List organised output tree |
| DELETE | `/api/v1/documents/input` | Clear INPUT_DIR |
| DELETE | `/api/v1/documents/output` | Clear OUTPUT_DIR |

### Faces

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/faces/match` | Match photos in `output/_unknown/` to known persons |

---

## Workflow

```
1. POST /documents/upload   →  files land in storage/input/
2. POST /documents/process  →  Gemini classifies → storage/output/<person>/<doc_type>.pdf
3. POST /faces/match        →  unknown photos matched to CCCD faces
4. GET  /documents/output   →  inspect organised results
```

---

## Document Types

| Value | Meaning |
|---|---|
| `CCCD` | Căn cước công dân |
| `Bang_dai_hoc` | Bằng đại học |
| `Giay_kham_suc_khoe` | Giấy khám sức khỏe |
| `Anh_the` | Ảnh thẻ |
| `Ly_lich` | Lý lịch tự thuật |
| `Khac` | Tài liệu khác |

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *required* | Google Generative AI key |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Model name |
| `INPUT_DIR` | `storage/input` | Where uploaded files are staged |
| `OUTPUT_DIR` | `storage/output` | Where organised files land |
| `FACE_MODEL` | `Facenet512` | DeepFace model |
| `FACE_DETECTOR` | `retinaface` | Face detector backend |
| `FACE_THRESHOLD` | `0.4` | Cosine distance threshold |
| `DEBUG` | `false` | Enable debug logging |
