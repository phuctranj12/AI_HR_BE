from urllib.parse import urlparse, urlunparse

import psycopg2


def _db_name_from_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    name = (parsed.path or "").lstrip("/")
    return name or "postgres"


def _maintenance_url(database_url: str, maintenance_db: str = "postgres") -> str:
    parsed = urlparse(database_url)
    # Replace path with maintenance DB.
    new = parsed._replace(path=f"/{maintenance_db}")
    return urlunparse(new)


def ensure_database_exists(database_url: str) -> None:
    """Create the target database from DATABASE_URL if missing.

    This lets deployments run without manually creating employee_management first.
    Requires the configured user to have CREATEDB privilege.
    """
    dbname = _db_name_from_url(database_url)
    maintenance_url = _maintenance_url(database_url, "postgres")

    conn = psycopg2.connect(maintenance_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            exists = cur.fetchone() is not None
            if not exists:
                cur.execute(f'CREATE DATABASE "{dbname}"')
    finally:
        conn.close()

