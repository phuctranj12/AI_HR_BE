from typing import Annotated, Any

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.db.postgres import connect
from app.services.hr_service import HRService


def get_hr_service(settings: Settings = Depends(get_settings)) -> HRService:
    return HRService(settings)


def get_db(request: Request, settings: Settings = Depends(get_settings)) -> Any:
    # Prefer the shared lifespan connection (normal server runtime).
    conn = getattr(request.app.state, "db", None)
    if conn is not None:
        return conn

    # Fallback for contexts where lifespan isn't running (tests/CLI).
    return connect(settings.database_url)


SettingsDep = Annotated[Settings, Depends(get_settings)]
HRServiceDep = Annotated[HRService, Depends(get_hr_service)]
DbDep = Annotated[Any, Depends(get_db)]
