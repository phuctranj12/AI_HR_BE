import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
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
    status_id: Optional[int] = None
    date_of_birth: Optional[str] = None
    hometown: Optional[str] = None
    join_date: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    permanent_address: Optional[str] = None
    position: Optional[str] = None
    file_path: Optional[str] = None
    notes: Optional[str] = None

def connect(database_url: str):
    ensure_database_exists(database_url)
    conn = psycopg2.connect(database_url)
    return conn

def create_pool(database_url: str, minconn: int = 1, maxconn: int = 20) -> ThreadedConnectionPool:
    ensure_database_exists(database_url)
    return ThreadedConnectionPool(minconn, maxconn, database_url)

def init_db(conn) -> None:
    init_schema(conn)

def get_status_id_by_name(conn, status_name: str) -> Optional[int]:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM statuses WHERE status_name = %s", (status_name,))
        row = cur.fetchone()
        return row[0] if row else None

def get_employee_by_code(conn, employee_code: str) -> Optional[Employee]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT 
                id, employee_code, full_name, folder_path, created_at, updated_at, status_id,
                date_of_birth::text, hometown, join_date::text, department, phone, email, 
                permanent_address, position, file_path, notes
            FROM employees WHERE employee_code = %s
            """,
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
    date_of_birth: Optional[str] = None,
    hometown: Optional[str] = None,
    join_date: Optional[str] = None,
    department: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    permanent_address: Optional[str] = None,
    position: Optional[str] = None,
) -> Employee:
    # Get active status ID
    active_id = get_status_id_by_name(conn, 'Active')
    
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO employees (
                employee_code, full_name, folder_path, status_id,
                date_of_birth, hometown, join_date, department,
                phone, email, permanent_address, position
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (employee_code) DO UPDATE SET
              full_name = COALESCE(EXCLUDED.full_name, employees.full_name),
              folder_path = EXCLUDED.folder_path,
              status_id = EXCLUDED.status_id,
              date_of_birth = COALESCE(EXCLUDED.date_of_birth, employees.date_of_birth),
              hometown = COALESCE(EXCLUDED.hometown, employees.hometown),
              join_date = COALESCE(EXCLUDED.join_date, employees.join_date),
              department = COALESCE(EXCLUDED.department, employees.department),
              phone = COALESCE(EXCLUDED.phone, employees.phone),
              email = COALESCE(EXCLUDED.email, employees.email),
              permanent_address = COALESCE(EXCLUDED.permanent_address, employees.permanent_address),
              position = COALESCE(EXCLUDED.position, employees.position)
            """,
            (
                employee_code, full_name, folder_path, active_id,
                date_of_birth, hometown, join_date, department,
                phone, email, permanent_address, position
            ),
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
    issued_date: Optional[str] = None,
    issued_by: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    document_number: Optional[str] = None,
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
            INSERT INTO documents (
                employee_id, document_type_id, document_name, file_path,
                issued_date, issued_by, start_date, end_date, document_number
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (employee_id, doc_type_id, filename, rel_path, issued_date, issued_by, start_date, end_date, document_number),
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

def rename_employee_documents_folder(conn, employee_id: int, old_folder: str, new_folder: str) -> None:
    """Update file_path for all documents belonging to an employee when their root folder is renamed."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE documents
            SET file_path = REGEXP_REPLACE(file_path, '^' || %s || '/', %s || '/')
            WHERE employee_id = %s AND file_path LIKE %s || '/%%'
            """,
            (old_folder, new_folder, employee_id, old_folder)
        )
    conn.commit()

def delete_employee_and_documents(conn, normalized_name: str, hard_delete: bool = False) -> bool:
    emp = get_employee_by_code(conn, normalized_name)
    if not emp:
        return False
        
    terminated_id = get_status_id_by_name(conn, 'Terminated')
    
    with conn.cursor() as cur:
        cur.execute("SELECT status_id FROM employees WHERE id = %s", (emp.id,))
        row = cur.fetchone()
        current_status_id = row[0] if row else None
        
        if current_status_id != terminated_id and not hard_delete:
            cur.execute("UPDATE employees SET status_id = %s WHERE id = %s", (terminated_id, emp.id))
            conn.commit()
            return False
            
        cur.execute("DELETE FROM project_employees WHERE employee_id = %s", (emp.id,))
        cur.execute("DELETE FROM documents WHERE employee_id = %s", (emp.id,))
        cur.execute("DELETE FROM employees WHERE id = %s", (emp.id,))
    conn.commit()
    return True

def clear_all_data(conn) -> None:
    # Not used by the current flow; kept for future use.
    return
