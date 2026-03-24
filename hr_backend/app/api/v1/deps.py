from typing import Annotated, Any

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.db.postgres import connect
from app.services.hr_service import HRService


def get_hr_service(settings: Settings = Depends(get_settings)) -> HRService:
    return HRService(settings)


def get_db(request: Request, settings: Settings = Depends(get_settings)) -> Any:
    # Prefer the pooled connection (normal server runtime).
    pool = getattr(request.app.state, "db_pool", None)
    if pool is not None:
        conn = pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            pool.putconn(conn)
    else:
        # Fallback for contexts where lifespan isn't running (tests/CLI).
        conn = connect(settings.database_url)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


SettingsDep = Annotated[Settings, Depends(get_settings)]
HRServiceDep = Annotated[HRService, Depends(get_hr_service)]
DbDep = Annotated[Any, Depends(get_db)]
