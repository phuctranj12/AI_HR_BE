import psycopg2
from psycopg2.extras import RealDictCursor
from dataclasses import dataclass
from typing import Optional

from app.db.postgres_schema import init_schema
from app.db.postgres_bootstrap import ensure_database_exists

@dataclass(frozen=True)
class Employee:
    id: int
    employee_code: Optional[str]
    full_name: str
    folder_path: str
    created_at: str
    updated_at: str

def connect(database_url: str):
    ensure_database_exists(database_url)
    conn = psycopg2.connect(database_url)
    return conn

def init_db(conn) -> None:
    init_schema(conn)

def get_employee_by_code(conn, employee_code: str) -> Optional[Employee]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id, employee_code, full_name, folder_path, created_at, updated_at FROM employees WHERE employee_code = %s",
            (employee_code,),
        )
        row = cur.fetchone()
        return Employee(**row) if row else None

def upsert_employee(
    conn,
    *,
    employee_code: str,
    full_name: str,
    folder_path: str,
) -> Employee:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO employees (employee_code, full_name, folder_path)
            VALUES (%s, %s, %s)
            ON CONFLICT (employee_code) DO UPDATE SET
              full_name = EXCLUDED.full_name,
              folder_path = EXCLUDED.folder_path
            """,
            (employee_code, full_name, folder_path),
        )
    conn.commit()
    emp = get_employee_by_code(conn, employee_code)
    assert emp is not None
    return emp

def insert_document(
    conn,
    *,
    employee_id: int,
    doc_type: str,
    filename: str,
    rel_path: str,
) -> None:
    with conn.cursor() as cur:
        # ensure doc_type exists in document_types
        cur.execute("SELECT id FROM document_types WHERE type_name = %s", (doc_type,))
        row = cur.fetchone()
        if row:
            doc_type_id = row[0]
        else:
            cur.execute("INSERT INTO document_types (type_name) VALUES (%s) RETURNING id", (doc_type,))
            doc_type_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO documents (employee_id, document_type_id, document_name, file_path)
            VALUES (%s, %s, %s, %s)
            """,
            (employee_id, doc_type_id, filename, rel_path),
        )
    conn.commit()

def delete_document(conn, employee_id: int, filename: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM documents WHERE employee_id = %s AND document_name = %s",
            (employee_id, filename),
        )
    conn.commit()

def rename_document(conn, employee_id: int, old_filename: str, new_filename: str, new_rel_path: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE documents 
            SET document_name = %s, file_path = %s
            WHERE employee_id = %s AND document_name = %s
            """,
            (new_filename, new_rel_path, employee_id, old_filename),
        )
    conn.commit()

def delete_employee_and_documents(conn, normalized_name: str) -> None:
    emp = get_employee_by_code(conn, normalized_name)
    if not emp:
        return
    with conn.cursor() as cur:
        cur.execute("DELETE FROM documents WHERE employee_id = %s", (emp.id,))
        cur.execute("DELETE FROM employees WHERE id = %s", (emp.id,))
    conn.commit()

def clear_all_data(conn) -> None:
    # Not used by the current flow; kept for future use.
    return
