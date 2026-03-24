import logging

from fastapi import APIRouter, HTTPException, status

from app.api.v1.deps import HRServiceDep, DbDep
from app.schemas.hr import MatchFacesResponse

router = APIRouter(prefix="/faces", tags=["faces"])
logger = logging.getLogger(__name__)


@router.post(
    "/match",
    summary="Match unknown photos to known persons using face recognition",
    response_model=MatchFacesResponse,
)
def match_faces(hr: HRServiceDep, db: DbDep) -> MatchFacesResponse:
    """For each image in people/_unknown:

    1. Build anchor embeddings from CCCD.pdf files of known persons.
    2. Compare the unknown photo against all anchors (cosine distance).
    3. Copy the photo to the best-matching person folder as Anh_the.<ext>.
    """
    try:
        return hr.match_faces(db)
    except Exception as exc:
        logger.exception("match_faces failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
