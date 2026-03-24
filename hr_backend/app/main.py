from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hr_backend.app.api.v1.router import router as api_v1_router
from hr_backend.app.core.config import get_settings
from hr_backend.app.core.logging import configure_logging
from hr_backend.app.db.postgres import connect, create_pool, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.debug)
    # Ensure storage directories exist on startup
    settings.input_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.people_dir.mkdir(parents=True, exist_ok=True)

    pool = create_pool(settings.database_url)
    conn = pool.getconn()
    try:
        init_db(conn)
        conn.commit()
    finally:
        pool.putconn(conn)
        
    app.state.db_pool = pool
    yield
    try:
        pool.closeall()
    except Exception:
        pass


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router)
    return app


app = create_app()
