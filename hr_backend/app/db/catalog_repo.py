from psycopg2.extras import RealDictCursor


# ── Document types ──────────────────────────────────────────────────────────

def list_document_types(conn) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id, type_name FROM document_types ORDER BY type_name")
        return list(cur.fetchall())


def create_document_type(conn, type_name: str) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO document_types (type_name)
            VALUES (%s)
            ON CONFLICT (type_name) DO UPDATE SET type_name = EXCLUDED.type_name
            RETURNING id, type_name
            """,
            (type_name,),
        )
        row = cur.fetchone()
    conn.commit()
    return dict(row)


def delete_document_type(conn, doc_type_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM document_types WHERE id = %s", (doc_type_id,))
        if cur.rowcount == 0:
            raise KeyError("document type not found")
    conn.commit()


# ── Statuses ────────────────────────────────────────────────────────────────

def list_statuses(conn) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id, status_name FROM statuses ORDER BY id")
        return list(cur.fetchall())

