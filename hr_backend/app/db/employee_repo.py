from psycopg2.extras import RealDictCursor


def list_employees(conn, q=None, limit: int = 50) -> list[dict]:
    q = (q or "").strip()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if q:
            cur.execute(
                """
                SELECT id, employee_code, full_name, department, position, phone, email, folder_path, created_at, updated_at
                FROM employees
                WHERE lower(full_name) LIKE lower(%s) OR lower(employee_code) LIKE lower(%s)
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (f"%{q}%", f"%{q}%", limit),
            )
        else:
            cur.execute(
                """
                SELECT id, employee_code, full_name, department, position, phone, email, folder_path, created_at, updated_at
                FROM employees
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (limit,),
            )
        return list(cur.fetchall())


def get_employee(conn, employee_id: int) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, employee_code, full_name, date_of_birth, hometown, join_date, department, phone, email,
                   permanent_address, folder_path, position, file_path, created_at, updated_at, notes, status_id
            FROM employees
            WHERE id = %s
            """,
            (employee_id,),
        )
        row = cur.fetchone()
        if not row:
            raise KeyError("employee not found")
        return dict(row)


def create_employee(conn, data: dict) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO employees (
                full_name, employee_code, date_of_birth, hometown, join_date, department, phone, email,
                permanent_address, folder_path, position, file_path, notes, status_id
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id, employee_code, full_name, department, position, phone, email, folder_path, created_at, updated_at
            """,
            (
                data.get("full_name"),
                data.get("employee_code"),
                data.get("date_of_birth"),
                data.get("hometown"),
                data.get("join_date"),
                data.get("department"),
                data.get("phone"),
                data.get("email"),
                data.get("permanent_address"),
                data.get("folder_path"),
                data.get("position"),
                data.get("file_path"),
                data.get("notes"),
                data.get("status_id"),
            ),
        )
        row = cur.fetchone()
    conn.commit()
    return dict(row)


def update_employee(conn, employee_id: int, data: dict) -> dict:
    allowed = (
        "full_name",
        "employee_code",
        "date_of_birth",
        "hometown",
        "join_date",
        "department",
        "phone",
        "email",
        "permanent_address",
        "folder_path",
        "position",
        "file_path",
        "notes",
        "status_id",
    )
    sets = []
    vals = []
    for k in allowed:
        if k in data:
            sets.append(f"{k} = %s")
            vals.append(data[k])
    if not sets:
        return get_employee(conn, employee_id)

    vals.append(employee_id)
    q = f"""
        UPDATE employees
        SET {", ".join(sets)}
        WHERE id = %s
        RETURNING id, employee_code, full_name, department, position, phone, email, folder_path, created_at, updated_at
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q, tuple(vals))
        row = cur.fetchone()
    conn.commit()
    if not row:
        raise KeyError("employee not found")
    return dict(row)


def delete_employee(conn, employee_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM employees WHERE id = %s", (employee_id,))
        if cur.rowcount == 0:
            raise KeyError("employee not found")
    conn.commit()

