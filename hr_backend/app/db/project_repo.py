from typing import Any, Optional

from psycopg2.extras import RealDictCursor


def list_projects(conn) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, project_name, location, function, scale, start_date, end_date, status_id, tree_data
            FROM projects
            ORDER BY id DESC
            """
        )
        return list(cur.fetchall())


def create_project(conn, data: dict) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO projects (project_name, location, function, scale, start_date, end_date, status_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, project_name, location, function, scale, start_date, end_date, status_id, tree_data
            """,
            (
                data.get("project_name"),
                data.get("location"),
                data.get("function"),
                data.get("scale"),
                data.get("start_date"),
                data.get("end_date"),
                data.get("status_id"),
            ),
        )
        row = cur.fetchone()
    conn.commit()
    return dict(row)


def update_project(conn, project_id: int, data: dict) -> dict:
    fields = []
    values: list[Any] = []
    for key in ("project_name", "location", "function", "scale", "start_date", "end_date", "status_id"):
        if key in data and data[key] is not None:
            fields.append(f"{key} = %s")
            values.append(data[key])
    if not fields:
        return get_project(conn, project_id)

    values.append(project_id)
    q = f"""
        UPDATE projects
        SET {", ".join(fields)}
        WHERE id = %s
        RETURNING id, project_name, location, function, scale, start_date, end_date, status_id, tree_data
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q, tuple(values))
        row = cur.fetchone()
    conn.commit()
    if not row:
        raise KeyError("project not found")
    return dict(row)


def delete_project(conn, project_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))
        if cur.rowcount == 0:
            raise KeyError("project not found")
    conn.commit()


def get_project(conn, project_id: int) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, project_name, location, function, scale, start_date, end_date, status_id, tree_data
            FROM projects
            WHERE id = %s
            """,
            (project_id,),
        )
        row = cur.fetchone()
        if not row:
            raise KeyError("project not found")
        return dict(row)


def list_project_members(conn, project_id: int) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT pe.employee_id, pe.project_id, pe.role, pe.start_date, pe.end_date,
                   e.full_name, e.employee_code, e.department, e.position
            FROM project_employees pe
            JOIN employees e ON e.id = pe.employee_id
            WHERE pe.project_id = %s
            ORDER BY e.full_name
            """,
            (project_id,),
        )
        return list(cur.fetchall())


def add_project_member(
    conn,
    *,
    project_id: int,
    employee_id: int,
    role: Optional[str],
    start_date,
    end_date,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO project_employees (employee_id, project_id, role, start_date, end_date)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (employee_id, project_id) DO UPDATE SET
              role = EXCLUDED.role,
              start_date = EXCLUDED.start_date,
              end_date = EXCLUDED.end_date
            """,
            (employee_id, project_id, role, start_date, end_date),
        )
    conn.commit()


def remove_project_member(conn, *, project_id: int, employee_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM project_employees WHERE project_id = %s AND employee_id = %s",
            (project_id, employee_id),
        )
    conn.commit()


def list_project_requirements(conn, project_id: int) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT pr.project_id, pr.document_type_id, dt.type_name
            FROM project_requirements pr
            JOIN document_types dt ON dt.id = pr.document_type_id
            WHERE pr.project_id = %s
            ORDER BY dt.type_name
            """,
            (project_id,),
        )
        return list(cur.fetchall())


def set_project_requirements(conn, project_id: int, document_type_ids: list[int]) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM project_requirements WHERE project_id = %s", (project_id,))
        for dt_id in document_type_ids:
            cur.execute(
                """
                INSERT INTO project_requirements (project_id, document_type_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (project_id, dt_id),
            )
    conn.commit()


def add_project_members_batch(conn, project_id: int, members: list[dict]) -> None:
    with conn.cursor() as cur:
        for member in members:
            cur.execute(
                """
                INSERT INTO project_employees (employee_id, project_id, role, start_date, end_date)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (employee_id, project_id) DO UPDATE SET
                  role = EXCLUDED.role,
                  start_date = EXCLUDED.start_date,
                  end_date = EXCLUDED.end_date
                """,
                (member['employee_id'], project_id, member.get('role'), member.get('start_date'), member.get('end_date')),
            )
    conn.commit()


def update_project_tree(conn, project_id: int, tree_data: Any) -> None:
    import json
    with conn.cursor() as cur:
        cur.execute("UPDATE projects SET tree_data = %s WHERE id = %s", (json.dumps(tree_data) if tree_data else None, project_id))
    conn.commit()


